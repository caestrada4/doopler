# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Conciliaciones Bancarias',
    'version': '16.0',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'depends': [
        'web','account_accountant',
    ],
    'author': 'Danner Marante',
    'website': '',
    'assets': {
        'web.assets_backend': [
            'l16n_ec_reconcile/static/src/js/bank_conciliation.js',
            'l16n_ec_reconcile/static/src/js/mov_bancarios.js',
            'l16n_ec_reconcile/static/src/xml/banck_move.xml',
            'l16n_ec_reconcile/static/src/xml/bank_conciliation.xml',
            ]
    },
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/conciliacion.xml',
        # 'views/cargas_iniciales.xml',
        'views/reporte.xml',
        'views/extracto_reporte.xml',
        'data/sequence.xml',
        'wizard/conciliacion_manual.xml'
    ]
}
