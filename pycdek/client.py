# -*- coding: utf-8 -*-
import json
import hashlib
import datetime
import urllib2
import StringIO
from urllib import urlencode
from xml.etree import ElementTree
from abc import ABCMeta, abstractmethod


class AbstractOrder(object):
    __metaclass__ = ABCMeta

    def get_number(self):
        """ Номер заказа """
        return getattr(self, 'number')
        
    @abstractmethod
    def get_products(self):
        """ Список товаров """

    def get_sender_city_id(self):
        """ ID города отправителя по базе СДЭК """
        return getattr(self, 'sender_city_id')

    def get_sender_postcode(self):
        """ Почтовый индекс отправителя """
        return getattr(self, 'sender_city_postcode')

    def get_recipient_name(self):
        """ Имя получателя """
        return getattr(self, 'recipient_name')

    def get_recipient_phone(self):
        """ Номер телефона получателя """
        return getattr(self, 'recipient_phone')

    def get_recipient_city_id(self):
        """ ID города получателя по базе СДЭК """
        return getattr(self, 'recipient_city_id')

    def get_recipient_postcode(self):
        """ Почтовый индекс получателя """
        return getattr(self, 'recipient_city_postcode')

    def get_recipient_address_street(self):
        """ Улица адреса доставки """
        return getattr(self, 'recipient_address_street')

    def get_recipient_address_house(self):
        """ Номер дома адреса доставки """
        return getattr(self, 'recipient_address_house')

    def get_recipient_address_flat(self):
        """ Номер квартиры адреса доставки """
        return getattr(self, 'recipient_address_flat')

    def get_pvz_code(self):
        """ Код пункта самовывоза """
        return getattr(self, 'pvz_code')

    def get_shipping_tariff(self):
        """ ID тарифа доставки """
        return getattr(self, 'shipping_tariff')

    def get_shipping_price(self):
        """ Стоимость доставки """
        return getattr(self, 'shipping_price')

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

    def get_quantity(self):
        """ Количество """
        return getattr(self, 'quantity')

    @abstractmethod
    def get_product_price(self):
        """ Цена за единицу товара """

    @abstractmethod
    def get_product_payment(self):
        """ Цена за единицу товара, которую клиент должен оплатить при получении """


class Client(object):
    INTEGRATOR_URL = 'http://gw.edostavka.ru:11443'
    CALCULATOR_URL = 'http://api.cdek.ru/calculator/calculate_price_by_json.php'
    CREATE_ORDER_URL = INTEGRATOR_URL + '/new_orders.php'
    DELETE_ORDER_URL = INTEGRATOR_URL + '/delete_orders.php'
    ORDER_STATUS_URL = INTEGRATOR_URL + '/status_report_h.php'
    ORDER_INFO_URL = INTEGRATOR_URL + '/info_report.php'
    ORDER_PRINT_URL = INTEGRATOR_URL + '/orders_print.php'
    DELIVERY_POINTS_URL = INTEGRATOR_URL + '/pvzlist.php'
    CALL_COURIER_URL = INTEGRATOR_URL + '/call_courier.php'
    array_tags = {'State', 'Delay', 'Good', 'Fail', 'Item', 'Package'}

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

        return urllib2.urlopen(request).read()

    @classmethod
    def _parse_xml(cls, data):
        try:
            xml = ElementTree.fromstring(data)
        except ElementTree.ParseError:
            pass
        else:
            return xml

    @classmethod
    def _xml_to_dict(cls, xml):
        result = xml.attrib

        for child in xml.getchildren():
            if child.tag in cls.array_tags:
                result[child.tag] = result.get(child.tag, [])
                result[child.tag].append(cls._xml_to_dict(child))
            else:
                result[child.tag] = cls._xml_to_dict(child)

        return result

    @classmethod
    def get_shipping_cost(cls, sender_city_data, recipient_city_data, tariffs, goods):
        """
        Возвращает информацию о стоимости и сроках доставки
        Для отправителя и получателя обязателен один из параметров: *_city_id или *_city_postcode внутри *_city_data
        :param sender_city_data: {id: '', postcode: ''} ID и/или почтовый индекс города отправителя по базе СДЭК
        :param recipient_city_data: {id: '', postcode: ''} ID и/или почтовый индекс города получателя по базе СДЭК
        :param tariffs: список тарифов
        :param goods: список товаров
        :returns dict
        """
        params = {
            'version': '1.0',
            'dateExecute': datetime.date.today().isoformat(),
            'senderCityId': sender_city_data.get('id'),
            'receiverCityId': recipient_city_data.get('id'),
            'senderCityPostCode': sender_city_data.get('postcode'),
            'receiverCityPostCode': recipient_city_data.get('postcode'),
            'tariffList': [{'priority': -i, 'id': tariff} for i, tariff in enumerate(tariffs, 1)],
            'goods': goods,
        }

        return json.loads(cls._exec_request(cls.CALCULATOR_URL, json.dumps(params), 'POST'))

    @classmethod
    def get_delivery_points(cls, city_id=None):
        """
        Возвращает списков пунктов самовывоза для указанного города, либо для всех если город не указан
        :param city_id: ID города по базе СДЭК
        :returns list
        """
        response = cls._exec_request(cls.DELIVERY_POINTS_URL, {'cityid': city_id} if city_id else {})
        xml = cls._parse_xml(response)

        return [cls._xml_to_dict(point) for point in xml.findall('Pvz')]

    def _xml_to_string(self, xml):
        buff = StringIO.StringIO()
        ElementTree.ElementTree(xml).write(buff, encoding='UTF-8', xml_declaration=False)

        return '<?xml version="1.0" encoding="UTF-8" ?>' + buff.getvalue()

    def _exec_xml_request(self, url, xml_element):
        date = datetime.datetime.now().isoformat()
        xml_element.attrib['Date'] = date
        xml_element.attrib['Account'] = self._login
        xml_element.attrib['Secure'] = self._make_secure(date)

        response = self._exec_request(url, urlencode({'xml_request': self._xml_to_string(xml_element)}), method='POST')
        return self._parse_xml(response)

    def _make_secure(self, date):
        return hashlib.md5('%s&%s' % (date, self._password)).hexdigest()

    def create_order(self, order):
        """
        Создать заказ
        :param order: экземпляр класса AbstractOrder
        :returns dict
        """
        delivery_request_element = ElementTree.Element('DeliveryRequest', Number=str(order.get_number()), OrderCount='1')

        order_element = ElementTree.SubElement(delivery_request_element, 'Order')
        order_element.attrib['Number'] = str(order.get_number())
        order_element.attrib['SendCityCode'] = str(order.get_sender_city_id())
        order_element.attrib['SendCityPostCode'] = str(order.get_sender_postcode())
        order_element.attrib['RecCityCode'] = str(order.get_recipient_city_id())
        order_element.attrib['RecCityPostCode'] = str(order.get_recipient_postcode())
        order_element.attrib['RecipientName'] = order.get_recipient_name()
        order_element.attrib['TariffTypeCode'] = str(order.get_shipping_tariff())
        order_element.attrib['DeliveryRecipientCost'] = str(order.get_shipping_price())
        order_element.attrib['Phone'] = str(order.get_recipient_phone())
        order_element.attrib['Comment'] = order.get_comment()

        address_element = ElementTree.SubElement(order_element, 'Address')
        if order.get_pvz_code():
            address_element.attrib['PvzCode'] = order.get_pvz_code()
        else:
            address_element.attrib['Street'] = order.get_recipient_address_street()
            address_element.attrib['House'] = str(order.get_recipient_address_house())
            address_element.attrib['Flat'] = str(order.get_recipient_address_flat())

        package_element = ElementTree.SubElement(order_element, 'Package', Number='%s1' % order.get_number(), BarCode='%s1' % order.get_number())
        total_weight = 0

        for product in order.get_products():
            item_element = ElementTree.SubElement(package_element, 'Item', Amount=str(product.get_quantity()))
            item_element.attrib['Weight'] = str(product.get_product_weight())
            item_element.attrib['WareKey'] = str(product.get_product_upc())[:30]
            item_element.attrib['Cost'] = str(product.get_product_price())
            item_element.attrib['Payment'] = str(product.get_product_payment())

            total_weight += product.get_product_weight()

        package_element.attrib['Weight'] = str(total_weight)

        xml = self._exec_xml_request(self.CREATE_ORDER_URL, delivery_request_element)
        return self._xml_to_dict(xml.find('Order'))

    def delete_order(self, order):
        """
        Удалить заказ
        :param order: экземпляр класса AbstractOrder
        :returns dict
        """
        delete_request_element = ElementTree.Element('DeleteRequest', Number=str(order.get_number()), OrderCount='1')
        ElementTree.SubElement(delete_request_element, 'Order', Number=str(order.get_number()))

        xml = self._exec_xml_request(self.DELETE_ORDER_URL, delete_request_element)
        return self._xml_to_dict(xml.find('DeleteRequest'))

    def get_orders_info(self, orders_dispatch_numbers):
        """
        Информация по заказам
        :param orders_dispatch_numbers: список номеров отправлений СДЭК
        :returns list
        """
        info_request = ElementTree.Element('InfoRequest')
        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(info_request, 'Order', DispatchNumber=str(dispatch_number))

        xml = self._exec_xml_request(self.ORDER_INFO_URL, info_request)
        return [self._xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_statuses(self, orders_dispatch_numbers, show_history=True):
        """
        Статусы заказовx
        :param orders_dispatch_numbers: список номеров отправлений СДЭК
        :param show_history: получать историю статусов
        :returns list
        """
        status_report_element = ElementTree.Element('StatusReport', ShowHistory=str(int(show_history)))
        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(status_report_element, 'Order', DispatchNumber=str(dispatch_number))

        xml = self._exec_xml_request(self.ORDER_STATUS_URL, status_report_element)
        return [self._xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_print(self, orders_dispatch_numbers, copy_count=1):
        """
        Печатная форма квитанции к заказу
        :param orders_dispatch_numbers: список номеров отправлений СДЭК
        :param copy_count: количество копий
        """
        date = datetime.datetime.now().isoformat()
        orders_print_element = ElementTree.Element('OrdersPrint', OrderCount=str(len(orders_dispatch_numbers)), CopyCount=str(copy_count), Date=date, Account=self._login, Secure=self._make_secure(date))

        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(orders_print_element, 'Order', DispatchNumber=str(dispatch_number))

        response = self._exec_request(self.ORDER_PRINT_URL, urlencode({'xml_request': self._xml_to_string(orders_print_element)}), method='POST')

        return response if not response.startswith('<?xml') else None

    def call_courier(self, date, time_begin, time_end, sender_city_id, sender_phone, sender_name, weight, address_street, address_house, address_flat, comment='', lunch_begin=None, lunch_end=None):
        """
        Вызов курьера
        :param date: дата ожидания курьера
        :param time_begin: время начала ожидания
        :param time_end: время окончания ожидания
        :param sender_city_id: ID города отправителя по базе СДЭК
        :param sender_phone: телефон оправителя
        :param sender_name: ФИО оправителя
        :param weight: общий вес в граммах
        :param comment: комментарий
        :param lunch_begin: время начала обеда
        :param lunch_end: время окончания обеда
        :returns bool
        """
        call_courier_element = ElementTree.Element('CallCourier', CallCount='1')
        call_element = ElementTree.SubElement(call_courier_element, 'Call', Date=date.isoformat(), TimeBeg=time_begin.isoformat(), TimeEnd=time_end.isoformat())
        call_element.attrib['SendCityCode'] = str(sender_city_id)
        call_element.attrib['SendPhone'] = str(sender_phone)
        call_element.attrib['SenderName'] = sender_name
        call_element.attrib['Weight'] = str(weight)
        call_element.attrib['Comment'] = comment
        if lunch_begin:
            call_element.attrib['LunchBeg'] = lunch_begin.isoformat()
        if lunch_end:
            call_element.attrib['LunchEnd'] = lunch_end.isoformat()

        ElementTree.SubElement(call_element, 'Address', Street=address_street, House=str(address_house), Flat=str(address_flat))

        print self._xml_to_string(call_courier_element)

        try:
            self._exec_xml_request(self.CALL_COURIER_URL, call_courier_element)
        except urllib2.HTTPError:
            return False
        else:
            return True
