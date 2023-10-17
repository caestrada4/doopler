# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 18/10/2022
# Requerimiento:

{
    'name': 'Establecimientos y autorizaciones del SRI',
    'version': '16.0',
    'author': 'Danner Marante',
    'category': 'Localization',
    'complexity': 'normal',
    'license': 'AGPL-3',
    'website': '',
    'data': [
        'views/account_journal_view.xml',
        # 'data/account.ats.sustento.csv',
        # 'security/ir.model.access.csv'
    ],
    'depends': [
       'l16n_ec_partner',  
    ],
    "installable": True,
}
