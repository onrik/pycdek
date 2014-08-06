# -*- coding: utf-8 -*-
import json
import hashlib
import datetime
import urllib2
from urllib import urlencode
from lxml import etree


class CDEK(object):
    INTEGRATOR_URL = 'http://gw.edostavka.ru:11443'
    CALCULATOR_URL = 'http://api.cdek.ru/calculator/calculate_price_by_json.php'
    CREATE_ORDER_URL = INTEGRATOR_URL + '/new_orders.php'
    DELETE_ORDER_URL = INTEGRATOR_URL + '/delete_orders.php'
    ORDER_STATUS_URL = INTEGRATOR_URL + '/status_report_h.php'
    ORDER_INFO_URL = INTEGRATOR_URL + '/info_report.php'
    ORDER_PRINT_URL = INTEGRATOR_URL + '/orders_print.php'
    DELIVERY_POINTS_URL = INTEGRATOR_URL + '/pvzlist.php'

    def __init__(self, login=None, password=None):
        self._login = login
        self._password = password

    def _exec_request(self, url, data, method='GET'):
        if method == 'GET':
            request = urllib2.Request(url + '?' + urlencode(data))
        elif method == 'POST':
            request = urllib2.Request(url, data=data)
        else:
            raise NotImplementedError('Unknown method "%s"' % method)

        response = urllib2.urlopen(request).read()

        return response

    def _parse_xml(self, data):
        try:
            xml = etree.fromstring(data)
        except etree.XMLSyntaxError:
            pass
        else:
            return xml

    def _exec_xml_request(self, url, xml_element, date=None, method='POST'):
        date = (date or datetime.datetime.now()).isoformat()
        xml_element.attrib['Date'] = date
        xml_element.attrib['Account'] = self._login
        xml_element.attrib['Secure'] = self._make_secure(date)
        xml_request = '<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(xml_element, encoding="UTF-8")

        response = self._exec_request(url, urlencode({'xml_request': xml_request}), method)
        return self._parse_xml(response)

    def _make_secure(self, date):
        return hashlib.md5('%s&%s' % (date, self._password)).hexdigest()

    def get_shipping_cost(self, sender_city_id, receiver_city_id, tariffs, goods):
        """
        Возвращает информацию о стоимости и сроках доставки
        :param tariffs: список тарифов
        :param sender_city_id: ID города по базе СДЭК
        :param receiver_city_id: ID города по базе СДЭК
        :param goods: список товаров
        """
        date = datetime.datetime.now().isoformat()
        params = {
            'version': '1.0',
            'dateExecute': datetime.date.today().isoformat(),
            'senderCityId': sender_city_id,
            'receiverCityId': receiver_city_id,
            'tariffList': [{'priority': -i, 'id': tariff} for i, tariff in enumerate(tariffs, 1)],
            'goods': goods,
            'date': date,
        }
        if self._login:
            params.update({
                'account': self._login,
                'secure': self._make_secure(date)
            })

        response = json.loads(self._exec_request(self.CALCULATOR_URL, json.dumps(params), 'POST'))

        return response

    def get_delivery_points(self, city_id=None):
        """
        Возвращает списков пунктов самовывоза для указанного города, либо для всех если город не указан
        :param city_id: ID города по базе СДЭК
        """
        response = self._exec_request(self.DELIVERY_POINTS_URL, {'cityid': city_id} if city_id else {})
        xml = self._parse_xml(response)

        points = {}
        if xml is not None:
            for point in xml.xpath('//Pvz'):
                weight_limit = point.xpath('WeightLimit')
                points[point.attrib.get('Code')] = {
                    'name': point.attrib.get('Name'),
                    'code': point.attrib.get('Code'),
                    'address': point.attrib.get('Address', ''),
                    'phone': point.attrib.get('Phone'),
                    'worktime': point.attrib.get('WorkTime'),
                    'note': point.attrib.get('Note', ''),
                    'city_id': point.attrib.get('CityCode'),
                    'city_name': point.attrib.get('City'),
                    'coord_x': point.attrib.get('coordX'),
                    'coord_y': point.attrib.get('coordY'),
                    'weight_limit_min': weight_limit[0].attrib.get('WeightMin') if weight_limit else 0,
                    'weight_limit_max': weight_limit[0].attrib.get('WeightMax') if weight_limit else 0,
                }

        return points
