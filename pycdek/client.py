# -*- coding: utf-8 -*-
import json
import hashlib
import datetime
import urllib2
from urllib import urlencode
from abc import ABCMeta, abstractmethod
from lxml import etree


class AbstractOrder(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_number(self):
        """ Номер заказа """

    @abstractmethod
    def get_products(self):
        """ Список товаров """

    @abstractmethod
    def get_sender_city_id(self):
        """ ID города отправителя по базе СДЭК """

    @abstractmethod
    def get_recipient_name(self):
        """ Имя получателя """

    @abstractmethod
    def get_recipient_phone(self):
        """ Номер телефона получателя """

    @abstractmethod
    def get_recipient_city_id(self):
        """ ID города получателя по базе СДЭК """

    @abstractmethod
    def get_recipient_address_street(self):
        """ Улица адреса доставки """

    @abstractmethod
    def get_recipient_address_house(self):
        """ Номер дома адреса доставки """

    @abstractmethod
    def get_recipient_address_flat(self):
        """ Номер квартиры адреса доставки """

    @abstractmethod
    def get_pvz_code(self):
        """ Код пункта самовывоза """

    @abstractmethod
    def get_shipping_tariff(self):
        """ ID тарифа доставки """

    @abstractmethod
    def get_delivery_price(self):
        """ Стоимость доставки """

    def get_comment(self):
        """ Дополнительные инструкции для доставки """
        return ''


class AbstractOrderLine(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_product_title(self):
        """ Название товара """

    @abstractmethod
    def get_product_upc(self):
        """ Артикул товара """

    @abstractmethod
    def get_product_weight(self):
        """ Вес единицы товара в граммах """

    @abstractmethod
    def get_quantity(self):
        """ Количество """

    @abstractmethod
    def get_product_price(self):
        """ Цена за единицу товара """


class Client(object):
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

    def _exec_xml_request(self, url, xml_element):
        date = datetime.datetime.now().isoformat()
        xml_element.attrib['Date'] = date
        xml_element.attrib['Account'] = self._login
        xml_element.attrib['Secure'] = self._make_secure(date)
        xml_request = '<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(xml_element, encoding="UTF-8")

        response = self._exec_request(url, urlencode({'xml_request': xml_request}), method='POST')
        return self._parse_xml(response)

    def _make_secure(self, date):
        return hashlib.md5('%s&%s' % (date, self._password)).hexdigest()

    def create_order(self, order):
        delivery_request_element = etree.Element('DeliveryRequest', Number=str(order.get_number()), OrderCount='1')

        order_element = etree.SubElement(delivery_request_element, 'Order')
        order_element.attrib['Number'] = str(order.get_number())
        order_element.attrib['SendCityCode'] = str(order.get_sender_city_id())
        order_element.attrib['RecCityCode'] = str(order.get_recipient_city_id())
        order_element.attrib['RecipientName'] = order.get_recipient_name()
        order_element.attrib['TariffTypeCode'] = str(order.get_shipping_tariff())
        order_element.attrib['DeliveryRecipientCost'] = str(order.get_delivery_price())
        order_element.attrib['Phone'] = order.get_recipient_phone()
        order_element.attrib['Comment'] = order.get_comment()

        address_element = etree.SubElement(order_element, 'Address')
        if order.get_pvz_code():
            address_element.attrib['PvzCode'] = order.get_pvz_code()
        else:
            address_element.attrib['Street'] = order.get_recipient_address_street()
            address_element.attrib['House'] = str(order.get_recipient_address_house())
            address_element.attrib['Flat'] = str(order.get_recipient_address_flat())

        package_element = etree.SubElement(order_element, 'Package', Number='%s1' % order.get_number(), BarCode='%s1' % order.get_number())
        total_weight = 0

        for product in order.get_products():
            item_element = etree.SubElement(package_element, 'Item', Amount=str(product.get_quantity()))
            item_element.attrib['Weight'] = str(product.get_product_weight())
            item_element.attrib['WareKey'] = product.get_product_upc()[:30]
            item_element.attrib['Cost'] = str(product.get_product_price())
            item_element.attrib['Payment'] = str(product.get_product_price())

            total_weight += product.get_product_weight()

        package_element.attrib['Weight'] = str(total_weight)

        return self._exec_xml_request(self.CREATE_ORDER_URL, delivery_request_element)

    def delete_order(self, order):
        delete_request_element = etree.Element('DeleteRequest', Number=str(order.get_number()), OrderCount='1')
        etree.SubElement(delete_request_element, 'Order', Number=str(order.get_number()))

        return self._exec_xml_request(self.DELETE_ORDER_URL, delete_request_element)

    def get_orders_info(self, orders_dispatch_numbers):
        info_request_element = etree.Element('InfoRequest')
        for dispatch_number in orders_dispatch_numbers:
            etree.SubElement(info_request_element, 'Order', DispatchNumber=dispatch_number)

        return self._exec_xml_request(self.ORDER_INFO_URL, info_request_element)

    def get_orders_statuses(self, orders_dispatch_numbers, show_history=True):
        status_report_element = etree.Element('StatusReport', ShowHistory=str(int(show_history)))
        for dispatch_number in orders_dispatch_numbers:
            etree.SubElement(status_report_element, 'Order', DispatchNumber=dispatch_number)

        return self._exec_xml_request(self.ORDER_STATUS_URL, status_report_element)

    def get_orders_print(self, orders_dispatch_numbers, count=1):
        date = datetime.datetime.now().isoformat()
        orders_print_element = etree.Element('OrdersPrint', OrderCount=str(len(orders_dispatch_numbers)), CopyCount=str(count), Date=date, Account=self._login, Secure=self._make_secure(date))

        for dispatch_number in orders_dispatch_numbers:
            etree.SubElement(orders_print_element, 'Order', DispatchNumber=dispatch_number)

        request = '<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(orders_print_element, encoding="UTF-8")
        response = self._exec_request(self.ORDER_PRINT_URL, 'xml_request=' + request, method='POST')

        return response if not response.startswith('<?xml') else None
