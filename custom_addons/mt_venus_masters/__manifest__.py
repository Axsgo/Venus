{
    'name': 'Venus Masters',
    'version': '0.1',
    'Summary': 'Vehicle,driver and trip Masters',
    'author': 'Dyson',
    'description': 'Vehicle,driver and trip Masters',
    'category': 'Masters',
    'data': [
        'security/ir.model.access.csv',
        'security/master_security.xml',
        'data/mail_and_cron.xml',
        'views/vehicle_master_view.xml',
        'views/driver_master_view.xml',
        'views/trip_master_view.xml',
        'views/trip_location_master_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml'
    ],
    'depends': ['base','sale','purchase','sale_management'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
