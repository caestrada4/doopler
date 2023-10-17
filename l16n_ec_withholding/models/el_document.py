# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 29/03/2021
# Requerimiento: P00038


import base64
import io
import logging

from odoo import fields, models
from odoo.exceptions import Warning as UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from . import utils
from ..xades.sri import SriService


class AccountEpayment(models.Model):
    _name = 'account.epayment'

    code = fields.Char('Código')
    name = fields.Char('Forma de Pago')


class Edocument(models.AbstractModel):

    _name = 'account.edocument'
    _FIELDS = {
        'account.move': 'l10n_latam_document_number',
        'account.retention': 'name'
    }
    SriServiceObj = SriService()

    _logger = logging.getLogger(_name)

    def get_auth(self, document):
        """
        retorna la autorizacion
        :param document:
        :return:
        """
        partner = document.company_id.partner_id
        if document._name == 'account.invoice':
            return document.auth_inv_id
        elif document._name == 'account.retention':
            return partner.get_authorisation('ret_in_invoice')

    def get_secuencial(self):
        """
        retorna el secuencial
        :return:
        """
        return getattr(self, self._FIELDS[self._name])[8:]

    def _info_tributaria(self, document, access_key, emission_code):
        """
        Lista la informacion tributarios del documento
        :param document:
        :param access_key:
        :param emission_code:
        :return:
        """
        company = document.company_id
        auth = self.l10n_latam_document_type_id
        if self._name == 'account.retention':                 
            infoTributaria = {
                'ambiente': self.env.user.company_id.env_service,
                'tipoEmision': emission_code,
                'razonSocial': company.name,
                'nombreComercial': company.tradename,
                'ruc': company.partner_id.vat,
                'claveAcceso':  access_key,
                'codDoc': utils.tipoDocumento[auth.code],
                'estab': self.invoice_id.journal_id.l10n_ec_retention_entity,
                'ptoEmi': self.invoice_id.journal_id.l10n_ec_retention_emission,
                'secuencial': self.get_secuencial(),
                'dirMatriz': "{} {} ".format(company.street, company.street2)
            }
        else:
            infoTributaria = {
                'ambiente': self.env.user.company_id.env_service,
                'tipoEmision': emission_code,
                'razonSocial': company.name,
                'nombreComercial': company.tradename,
                'ruc': company.partner_id.vat,
                'claveAcceso':  access_key,
                'codDoc': utils.tipoDocumento[auth.code],
                'estab': self.journal_id.l10n_ec_entity,
                'ptoEmi': self.journal_id.l10n_ec_emission,
                'secuencial': self.get_secuencial(),
                'dirMatriz': "{} {} ".format(company.street, company.street2)
            }
        return infoTributaria

    def get_code(self):
        """
        Codigo de secuencial
        :return:
        """
        code = "{}".format(self.company_id.document_sequense).zfill(8)
        self.sudo().company_id.document_sequense += 1
        return code

    def get_access_key(self, name):
        """
        Retorna la clave de acceso
        :param name:
        :return:
        """
        if name == 'account.move':
            auth = self.l10n_latam_document_type_id
            ld = "{}{}{}".format(str(self.invoice_date.day).zfill(2), str(self.invoice_date.month).zfill(2),
                                 self.invoice_date.year)
            numero = getattr(self, 'l10n_latam_document_number').replace('-', '')
        
        elif name == 'account.retention':
            auth = self.l10n_latam_document_type_id
            ld = "{}{}{}".format(str(self.date.day).zfill(2), str(self.date.month).zfill(2),
                                 self.date.year)
            numero = getattr(self, 'name').replace('-', '')
        
        fecha = ''.join(ld)
        tcomp = utils.tipoDocumento[auth.code]
        ruc = self.company_id.partner_id.vat
        codigo_numero = self.get_code()
        tipo_emision = self.company_id.emission_code
        access_key = (
            [fecha, tcomp, ruc],
            [numero, codigo_numero, tipo_emision]
            )
        return access_key

    def _get_codes(self, name='account.move'):
        """
        retorna la cleve de acceso y e codigo de emision
        :param name:
        :return:
        """
        ak_temp = self.get_access_key(name)
        self.SriServiceObj.set_active_env(self.env.user.company_id.env_service)
        access_key = self.SriServiceObj.create_access_key(ak_temp)
        emission_code = self.company_id.emission_code
        return access_key, emission_code

    
    def check_before_sent(self):
        """
        Verifica los el documentos antes de enviarlos
        :return:
        """
        MESSAGE_SEQUENCIAL = ' '.join([
            u'Los comprobantes electrónicos deberán ser',
            u'enviados al SRI para su autorización en orden cronológico',
            'y secuencial. Por favor enviar primero el',
            ' comprobante inmediatamente anterior.'])
        FIELD = {
            'account.invoice': 'invoice_number',
            'account.retention': 'name'
        }
        number = getattr(self, FIELD[self._name])
        sql = ' '.join([
            "SELECT authorization_sri, %s FROM %s" % (FIELD[self._name], self._table),  
            "WHERE state='open' AND %s < '%s'" % (FIELD[self._name], number),  
            self._name == 'account.invoice' and "AND type = 'out_invoice'" or '',  
            "ORDER BY %s DESC LIMIT 1" % FIELD[self._name]
        ])
        self.env.cr.execute(sql)
        res = self.env.cr.fetchone()
        if not res:
            return True
        auth, number = res
        if auth is None and number:
            raise UserError(MESSAGE_SEQUENCIAL)
        return True

    def check_date(self, date_invoice):
        """
        Validar que el envío del comprobante electrónico
        se realice dentro de las 24 horas posteriores a su emisión
        """
        LIMIT_TO_SEND = 5
        MESSAGE_TIME_LIMIT = u' '.join([
            u'Los comprobantes electrónicos deben',
            u'enviarse con máximo 5 días desde su emisión.']
        )
        # dt = datetime.strptime(date_invoice, '%Y-%m-%d')
        # days = (datetime.now() - date_invoice).days
        #if days > LIMIT_TO_SEND:
        #    raise UserError(MESSAGE_TIME_LIMIT)

    
    def update_document(self, auth, codes):
        """
        Actualiza los datos de los documentos
        :param auth:
        :param codes:
        :return:
        """
        fecha = auth.fechaAutorizacion.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.write({
            'numero_autorizacion': auth.numeroAutorizacion,
            'estado_autorizacion': auth.estado,
            'ambiente': auth.ambiente,
            'fecha_autorizacion': fecha,  
            'autorizado_sri': True,
            'clave_acceso': codes[0],
            'emission_code': codes[1]
        })

    
    def add_attachment(self, xml_element, auth):
        buf = io.StringIO()
        buf.write(xml_element.encode('utf-8'))
        document = base64.encodestring(buf.getvalue())
        buf.close()
        attach = self.env['ir.attachment'].create(
            {
                'name': '{0}.xml'.format(self.clave_acceso),
                'datas': document,
                'datas_fname':  '{0}.xml'.format(self.clave_acceso),
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'
            },
        )
        return attach

    
    def send_document(self, attachments=None, tmpl=False):
        self.ensure_one()
        self._logger.info('Enviando documento electronico por correo')
        tmpl = self.env.ref(tmpl)
        tmpl.send_mail(  
            self.id,
            email_values={'attachment_ids': attachments}
        )
        self.sent = True
        return True

    def render_document(self, document, access_key, emission_code):
        pass
