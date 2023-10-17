# -*- coding: utf-8 -*-

import base64
import logging
import os

from jinja2 import Environment, FileSystemLoader

from odoo import models, fields
from odoo.exceptions import UserError

from . import utils
from ..xades.sri import DocumentXML
from ..xades.xades_sri import Xades

TEMPLATES = {
    'out_invoice': 'out_invoice.xml'
}


class AccountWithdrawing(models.Model):
    _name = 'account.retention'
    _inherit = ['account.retention', 'account.edocument']
    _logger = logging.getLogger(_name)

    def get_secuencial(self):
        return getattr(self, 'name')[8:17]

    def _info_withdrawing(self, withdrawing):
        """
        """
        # generar infoTributaria
        company = withdrawing.company_id
        partner = withdrawing.invoice_id.partner_id
        obligadoContabilidad = 'SI'
        if company.partner_id.property_account_position_id.name == u'Persona natural no obligada a llevar contabilidad':
            obligadoContabilidad = 'NO'
        infoCompRetencion = {
            'fechaEmision': "{}/{}/{}".format(str(withdrawing.date.day).zfill(2),str(withdrawing.date.month).zfill(2),withdrawing.date.year),
            'dirEstablecimiento': company.street,
            'obligadoContabilidad': obligadoContabilidad,
            'tipoIdentificacionSujetoRetenido': utils.tipoIdentificacion[partner.l10n_latam_identification_type_id.display_name],
            'razonSocialSujetoRetenido': partner.name,
            'identificacionSujetoRetenido': partner.vat,
            'periodoFiscal':"{}/{}".format(str(withdrawing.date.month).zfill(2),str(withdrawing.date.year)),
        }
        if company.company_registry and company.company_registry != 'NA':
            infoCompRetencion.update({'contribuyenteEspecial': company.company_registry})
        return infoCompRetencion

    def _impuestos(self, retention):
        """
        """

        def get_codigo_retencion(linea):
            if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat', 'ret_vat_srv']:
                return utils.tabla21[str(abs(int(line.tax_id.amount)))]
            elif line.tax_id.tax_group_id.l10n_ec_type in ['ret_ir']:
                code = line.tax_id.description
                return code
            else:
                return '8'

        impuestos = []
        for line in retention.move_ids:
            impuesto = {
                'codigo': utils.tabla20[line.tax_id.tax_group_id.l10n_ec_type],
                'codigoRetencion': get_codigo_retencion(line),
                'baseImponible': '%.2f' % (line.base),
                'porcentajeRetener': str(abs(line.tax_id.amount)),
                'valorRetenido': '%.2f' % (abs(line.amount)),
                'codDocSustento': retention.invoice_id.sustento_sri.code,
                'numDocSustento': retention.invoice_id.l10n_latam_document_number.replace('-',''),
                'fechaEmisionDocSustento': "{}/{}/{}".format(
                                                             str(retention.invoice_id.date.day).zfill(2),
                                                              str(retention.invoice_id.date.month).zfill(2),
                                                             retention.invoice_id.date.year)

            }
            
            impuestos.append(impuesto)
        return {'impuestos': impuestos}

    def render_document(self, document, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ewithdrawing_tmpl = env.get_template('ewithdrawing.xml')
        data = {}
        data.update(self._info_tributaria(document, access_key, emission_code))
        data.update(self._info_withdrawing(document))
        data.update(self._impuestos(document))
        data.update({'direccionCliente': document.partner_id.contact_address})
        email = document.partner_id.email
        
        data.update({'emailCliente': email})
        data.update({'importeTotal': abs(document.amount_total)})
        data.update({'telefono': document.partner_id.phone if document.partner_id.phone else '-' })
        edocument = ewithdrawing_tmpl.render(data)
        return edocument

    def render_authorized_document(self, autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        edocument_tmpl = env.get_template('authorized_withdrawing.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),
            'comprobante': autorizacion.comprobante
        }
        auth_withdrawing = edocument_tmpl.render(auth_xml)
        return auth_withdrawing

    pre_send_sri = fields.Boolean(default=False)

     
    def action_generate_document(self):

        # if self.authorization_sri == True:
        #     raise UserError(u'El documento ya fue enviado al SRI')
        error_msg = ''

        # try:
        for obj in self:
            if obj.authorization_number:
                access_key, emission_code = self._get_codes('account.retention')
            else:
                access_key = obj.authorization_number
                emission_code = self.company_id.emission_code
            ewithdrawing = self.render_document(obj, access_key, emission_code)
            inv_xml = DocumentXML(ewithdrawing, 'withdrawing')
            inv_xml.validate_xml()
            xades = Xades()
            file_pk12 = obj.company_id.electronic_signature
            password = obj.company_id.password_electronic_signature
            obj.authorization_number = access_key
            xades_error, signed_document = xades.sign(ewithdrawing, file_pk12, password)
            if xades_error:
                error_msg = signed_document
                raise UserError(error_msg)

            ok, estado, errores = inv_xml.send_receipt(signed_document)
            obj.authorization_state = estado
            if obj.company_id.env_service == '1':
                obj.environment = 'PRUEBAS'
            else:
                obj.environment = 'PRODUCCION'

            if not ok:
                error_msg = errores
                obj.authorization_state = f"{estado}: {errores}"
                obj.authorization_sri = False
                return False, errores
            else:
                obj.authorization_sri = True
        # except Exception as e:
        #     raise UserError(e.args)
        #

      
    def retention_print(self):
        return self.env['report'].get_action(
            self,
            'l10n_ec_einvoice.report_eretention'
        )
