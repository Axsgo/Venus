{
    'name': 'Venus Reports',
    'version': '0.1',
    'author': 'Dyson',
    'description': 'Custom Report',
    'category': 'Reports',
    'data': [
        'report/invoice_report.xml',
        'views/account_move_view.xml'
    ],
    'depends': ['base','sale','purchase','account'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
