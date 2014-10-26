# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from pycdek import AbstractOrder, AbstractOrderLine, Client


class Product(models.Model):
    title = models.CharField('Название', max_length=255)
    weight = models.PositiveIntegerField('Вес, гр.')
    price = models.DecimalField('Цена', max_digits=12, decimal_places=2)


class Order(AbstractOrder, models.Model):
    sender_city_id = 44  # Если отправляем всегда из Москвы
    recipient_name = models.CharField('Имя получателя', max_length=100)
    recipient_phone = models.CharField('Телефон', max_length=20)
    recipient_city_id = models.PositiveIntegerField()
    recipient_address_street = models.CharField('Улица', max_length=100, null=True, blank=True)
    recipient_address_house = models.PositiveIntegerField('Номер дома', max_length=100, null=True, blank=True)
    recipient_address_flat = models.PositiveIntegerField('Номер квартиры', max_length=100, null=True, blank=True)
    pvz_code = models.CharField('Код пункта самовывоза', max_length=10, null=True, blank=True)
    shipping_tariff = models.PositiveIntegerField('Тариф доставки')
    shipping_price = models.DecimalField('Стоимость доставки', max_digits=12, decimal_places=2, default=0)
    comment = models.TextField('Комментарий', blank=True)
    is_paid = models.BooleanField('Заказ оплачен', default=False)

    def get_number(self):
        return self.id

    def get_products(self):
        return self.lines.all()

    def get_comment(self):
        return self.comment


class OrderLine(AbstractOrderLine, models.Model):
    order = models.ForeignKey(Order, related_name='lines')
    product = models.ForeignKey(Product)
    quantity = models.PositiveIntegerField('Количество', default=1)

    def get_product_title(self):
        return self.product.title

    def get_product_upc(self):
        return self.product.id

    def get_product_weight(self):
        return self.product.weight

    def get_quantity(self):
        return self.quantity

    def get_product_price(self):
        return self.product.price

    def get_product_payment(self):
        if self.order.is_paid:
            return 0
        else:
            return self.product.price  # оплата при получении


client = Client('login', 'password')

product = Product.objects.create(title='Шлакоблок', weight=1000, price=500)

# заказ в Новосибирск с самовывозом
Order.objects.create(
    recipient_name='Иванов Иван Иванович',
    recipient_phone='+7 (999) 999-99-99',
    recipient_city_id=270,  # Новосибирск
    shipping_tariff=137,  # самовывоз
    is_paid=True
)

# заказ в Санкт-Петербург с курьерской доставкой и оплатой при получении
order = Order.objects.create(
    recipient_name='Иванов Иван Иванович',
    recipient_phone='+7 (999) 999-99-99',
    recipient_city_id=137,  # Санкт-Петербург
    recipient_address_street='пр. Ленина',
    recipient_address_house=1,
    recipient_address_flat=1,
    shipping_tariff=136,  # доставка курьером
    comment='Позвонить за час'
)

OrderLine.objects.create(product=product, order=order)

# создание заказа
response = client.create_order(order)
dispatch_number = response['DispatchNumber']

# получение накладной к заказу
with open('Заказ #%s.pdf' % order.get_number(), 'wb') as f:
    data = client.get_orders_print([dispatch_number])
    f.write(data)

# отслеживание статуса доставки заказа
client.get_orders_statuses([dispatch_number])

# получение информации о заказе
client.get_orders_info([dispatch_number])

# удаление (отмена) заказа
client.delete_order(order)
