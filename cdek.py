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

    def __init__(self, login, password):
        self._login = login
        self._password = password

    @classmethod
    def _exec_request(cls, url, data, method='GET'):
        if method == 'GET':
            request = urllib2.Request(url + '?' + urlencode(data))
        elif method == 'POST':
            request = urllib2.Request(url, data=data)
        else:
            raise NotImplementedError('Unknown method "%s"' % method)

        response = urllib2.urlopen(request).read()

        return response

    @classmethod
    def _parse_xml(cls, data):
        try:
            xml = etree.fromstring(data)
        except etree.XMLSyntaxError:
            pass
        else:
            return xml

    @classmethod
    def get_shipping_cost(cls, sender_city_id, receiver_city_id, tariffs, goods):
        """
        Возвращает информацию о стоимости и сроках доставки
        :param tariffs: список тарифов
        :param sender_city_id: ID города отправителя по базе СДЭК
        :param receiver_city_id: ID города получателя по базе СДЭК
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

        return json.loads(cls._exec_request(cls.CALCULATOR_URL, json.dumps(params), 'POST'))

    @classmethod
    def get_delivery_points(cls, city_id=None):
        """
        Возвращает списков пунктов самовывоза для указанного города, либо для всех если город не указан
        :param city_id: ID города по базе СДЭК
        """
        response = cls._exec_request(cls.DELIVERY_POINTS_URL, {'cityid': city_id} if city_id else {})
        return cls._parse_xml(response)

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

    def get_orders_info(self, orders):
        info_request_element = etree.Element('InfoRequest')
        for dispatch_number in orders:
            etree.SubElement(info_request_element, 'Order', DispatchNumber=dispatch_number)

        return self._exec_xml_request(self.ORDER_INFO_URL, info_request_element)

    def get_orders_statuses(cls, orders, show_history=True):
        status_report_element = etree.Element('StatusReport', ShowHistory=str(int(show_history)))
        for dispatch_number in orders:
            etree.SubElement(status_report_element, 'Order', DispatchNumber=dispatch_number)

        return cls._exec_xml_request(cls.ORDER_STATUS_URL, status_report_element)


    def delete_orders(self, orders):
        delete_request_element = etree.Element('DeleteRequest', OrderCount=str(len(orders)))
        for dispatch_number in orders:
            etree.SubElement(delete_request_element, 'Order', DispatchNumber=dispatch_number)

        return self._exec_xml_request(self.DELETE_ORDER_URL, delete_request_element)

    def get_orders_print(self, orders, count=1):
        date = datetime.datetime.now().isoformat()
        orders_print_element = etree.Element('OrdersPrint', OrderCount=str(len(orders)), CopyCount=str(count), Date=date, Account=self._login, Secure=self._make_secure(date))

        for dispatch_number in orders:
            etree.SubElement(orders_print_element, 'Order', DispatchNumber=dispatch_number)

        request = '<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(orders_print_element, encoding="UTF-8")
        response = self._exec_request(self.ORDER_PRINT_URL, 'xml_request=' + request, method='POST')

        return response if not response.startswith('<?xml') else None
