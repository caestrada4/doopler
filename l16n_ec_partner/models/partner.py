# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 29/03/2021
# Requerimiento: P00038

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from ..lib.validators import validate_cedula, validate_ruc

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'name')
    def name_get(self):
        """
        to string
        :return:
        """
        data = []
        for partner in self:
            display_val = u'{0} '.format(
                partner.name
            )
            data.append((partner.id, display_val))
        return data

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        """
        Busqueda por nombre
        :param name:
        :param args:
        :param operator:
        :param limit:
        :return:
        """

        if not args:
            args = []
        if name:
            partners = self.search([('vat', operator, name)] + args, limit=limit)  # noqa
            if not partners:
                partners = self.search([('name', operator, name)] + args, limit=limit)  # noqa
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()

    @api.constrains('vat')
    def _check_identifier(self):

        """
        Valida la identificacion
        :return:
        """
        for obj in self:
            if not obj.vat:
                raise ValidationError('Número de Identificación campo requerido')
            if obj.l10n_latam_identification_type_id.name != 'Pasaporte':
                partner = self.search(
                    [('vat', '=', obj.vat), ('company_id', '=', obj.env.user.company_id.id)])  # noqa
                if len(partner) > 0:
                    raise ValidationError('Cliente registrado en el sistema')
            res = False
            if obj.l10n_latam_identification_type_id.name == 'Cédula':
                res = validate_cedula(obj.vat)
            elif obj.l10n_latam_identification_type_id.name == 'RUC':
                res = validate_ruc(obj.vat)
            else:
                return True
            if not res:
                raise ValidationError('Número de Identificación incorrecto.')

    @api.depends('vat')
    def _person_type_compute(self):
        """
        Determina el tio de persona por la cedula
        :return:
        """
        for obj in self:
            if not obj.vat:
                obj.person_type = '0'
            elif int(obj.vat[2]) <= 6:
                obj.person_type = '6'
            elif int(obj.vat[2]) in [6, 9]:
                obj.person_type = '9'
            else:
                obj.person_type = '0'

    person_type = fields.Selection(
        compute='_person_type_compute',
        selection=[
            ('6', 'Persona Natural'),
            ('9', 'Persona Juridica'),
            ('0', 'Otro')
        ],
        string='Persona',
        store=True
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    tradename = fields.Char('Nombre Comercial', size=500)

    type_invoice = fields.Selection([('1', 'Electrónica'), ('2', 'Manual')], string='Tipo Facturación',
                                    required=True, default='1')
    special_taxpayer = fields.Selection(
        [
            ('NO', 'No'),
            ('Contribuyente Especial', 'Contribuyente Especial'),
            ('Régimen Microempresas', 'Régimen Microempresas'),
            ('CONTRIBUYENTE RÉGIMEN RIMPE', 'CONTRIBUYENTE RÉGIMEN RIMPE'),
            ('Régimen General', 'Régimen General')
        ],
        string='Contribuyente ',
        required=True,
        default='NO'
    )
    retention_agent = fields.Selection(
        [
            ('SI', 'SI'),
            ('NO', 'NO')
        ],
        string='Agente de Retención',
        default='NO'
    )
