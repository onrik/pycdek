# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from pycdek import AbstractOrder, AbstractOrderLine


class Product(models.Model):
    title = models.CharField('Название', max_length=255)
    upc = models.CharField('Артикул', max_length=255)
    weight = models.PositiveIntegerField('Вес, гр.')
    price = models.DecimalField('Цена', max_digits=12, decimal_places=2)


class Order(AbstractOrder, models.Model):
    recipient_name = models.CharField('Имя получателя', max_length=100)
    recipient_phone = models.CharField('Телефон', max_length=20)
    recipient_city_id = models.PositiveIntegerField()
    recipient_address_street = models.CharField('Улица', max_length=100, null=True, blank=True)
    recipient_address_house = models.PositiveIntegerField('Номер дома', max_length=100, null=True, blank=True)
    recipient_address_flat = models.PositiveIntegerField('Номер квартиры', max_length=100, null=True, blank=True)
    pvz_code = models.CharField('Код пункта самовывоза', max_length=10, null=True, blank=True)
    dispatch_number = models.CharField('Номер отправления СДЭК', max_length=100, null=True, blank=True)
    shipping_tariff = models.PositiveIntegerField('Тариф доставки')
    shipping_price = models.DecimalField('Стоимость доставки', max_digits=12, decimal_places=2)

    def get_number(self):
        return self.id

    def get_products(self):
        return self.lines.all()

    def get_sender_city_id(self):
        return 44  # Если отправляем всегда из Москвы

    def get_recipient_name(self):
        return self.recipient_name

    def get_recipient_phone(self):
        return self.recipient_phone

    def get_recipient_city_id(self):
        return self.recipient_city_id

    def get_recipient_address_street(self):
        return self.recipient_address_street

    def get_recipient_address_house(self):
        return self.recipient_address_house

    def get_recipient_address_flat(self):
        return self.recipient_address_flat

    def get_pvz_code(self):
        return self.pvz_code

    def get_shipping_tariff(self):
        return self.shipping_tariff

    def get_shipping_price(self):
        return self.shipping_price


class OrderLine(AbstractOrderLine, models.Model):
    order = models.ForeignKey(Order, related_name='lines')
    product = models.ForeignKey(Product)
    quantity = models.PositiveIntegerField('Количество', default=1)

    def get_product_title(self):
        return self.product.title

    def get_product_upc(self):
        return self.product.upc

    def get_product_weight(self):
        return self.product.weight

    def get_quantity(self):
        return self.quantity

    def get_product_price(self):
        return self.product.price