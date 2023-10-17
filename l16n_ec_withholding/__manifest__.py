# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Retenciones para Ecuador',
    'version': '16.0.1.0.0',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'l16n_ec_partner',
        'l10n_latam_invoice_document',
        'account_accountant'
    ],
    'author': 'danner.marante@citytech.ec',
    'website': '',
    # 'external_dependencies': {
    #     'python': ['xmlsig'],
    # },
    'data': [
        'views/withholding_supplier_view.xml',
        'views/withholding_customer_view.xml',
        'security/ir.model.access.csv',
        'data/account.fiscal.position.csv',
        'data/account.epayment.csv',
        'views/account_invoice.xml',
        'views/el_company.xml',
        # REPORTES
        'views/report/reports.xml',
        'views/report/report_account_withdrawing.xml',
        'views/report/report_account_move.xml',

    ]
}
