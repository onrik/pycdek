##PyCDEK
Библиотека для работы с API транспортной компании [СДЭК](http://cdek.ru/).

База городов, список тарифов и докуентация API доступна по ссылке: http://www.edostavka.ru/website/edostavka/upload/custom/files/CDEK_integrator.zip

Для получения логина и пароля необходимо [заключить договор](http://www.edostavka.ru/reglament.html) с транспортной компанией.

####Установка:

    pip install git+https://github.com/onrik/pycdek.git#egg=pycdek


#### Примеры использования:

```python
# получение пунктов самовывоза в Москве
for point in c.get_delivery_points(44).xpath('Pvz'):
    print point.attrib['Code'], point.attrib['Address']
```
