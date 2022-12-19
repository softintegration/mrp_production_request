# -*- coding: utf-8 -*- 


{
 'name': 'Manufacturing order request',
 'author': 'Soft-integration',
 'application': False,
 'installable': True,
 'auto_install': False,
 'qweb': [],
 'description': False,
 'images': [],
 'version': '1.0.1.12',
 'category': 'Manufacturing/Manufacturing',
 'demo': [],
 'depends': ['mrp'],
 'data': [
     'security/mrp_production_request_security.xml',
     'security/ir.model.access.csv',
     'data/mrp_production_request_data.xml',
     'views/mrp_production_request_views.xml',
     'views/mrp_production_views.xml',
     'wizard/mrp_production_create_views.xml'
    ],
 'license': 'LGPL-3',
 }