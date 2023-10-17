# -*- coding: utf-8 -*-

CODE701 = 'Error en fecha de retención. Tiene 5 días desde la fecha de factura para aplicar una retención.'
CODE702 = u'El número no es de 9 dígitos y/o no pertenece a la autorización seleccionada.'
CODE703 = u'Retención conciliada con la factura, no se puede anular.'
CODE704 = u'Las líneas de facturación deben tener un impuesto relacionado con el IVA.'
CODE705 = u'No ha configurado la autorización de retenciones.'

CODE801 = u'Número de retención incorrecto. Debe ser de 9 dígitos.'
CODE802 = u'Número de retención incorrecto. Debe ser de 15 dígitos'
CODE803 = u'Numero de retención  no pertenece a la secuencia de autorización'
CODE804 = u'No se permite borrar retenciones validadas.'
CODE805 = u'El documento fue marcado para anular.'
CODE806 = u'Debe ingresar el número de la retención.'
CODE807 = u'Ya se han emitido documentos de retención relacionados con esta factura.'
CODE808 = u'No puede anular un documento que ha sido enviado al SRI.'
CODE809 = u'No existe documento de retención relacionado con esta factura.'

CODE810 = u'Las notas de credito no pueden tener retenciones.'


import requests


tipoDocumento = {
    '01': '01',
    '04': '04',
    '03': '03',
    '05': '05',
    '06': '06',
    '07': '07',
    '42': '07',
    '18': '01',
}

tipoIdentificacion = {
    'RUC': '04',
    'Cédula': '05',
    'pasaporte': '06',
    'venta_consumidor_final': '07',
    'identificacion_exterior': '08',
    'placa': '09',
}

codigoImpuesto = {
    'vat12': '2',
    'vat0': '2',
    'ice': '3',
    'other': '5'
}

tabla17 = {
    'vat12': '2',
    'vat0': '2',
    'ice': '3',
    'irbpnr': '5'
}

tabla18 = {
    '0': '0',
    '12': '2',
    '14': '3',
    'novat': '6',
    'excento': '7'
}

tabla20 = {
    'ret_ir': '1',
    'withhold_vat': '2',
    'withhold_income_tax': '2',
    'ret_isd': '6'
}

tabla21 = {
    '10': '9',
    '20': '10',
    '30': '1',
    '50': '11',
    '70': '2',
    '100': '3'
}

tabla26 = {
    '1': '01',
    '3': '02'
}

def getTabla26(value):
    try:
        return tabla26[value]
    except:
        return '00'

codigoImpuestoRetencion = {
    'ret_ir': '1',
    'withhold_vat': '2',
    'withhold_vat': '2',
    'ice': '3',
}

tarifaImpuesto = {
    'vat0': '0',
    'vat': '2',
    'novat': '6',
    'other': '7',
}

MSG_SCHEMA_INVALID = u"El sistema generó el XML pero"
" el comprobante electrónico no pasa la validación XSD del SRI."

SITE_BASE_TEST = 'https://celcer.sri.gob.ec/'
SITE_BASE_PROD = 'https://cel.sri.gob.ec/'
WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'  # noqa
WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'  # noqa
WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'  # noqa
WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'  # noqa


def check_service(env='prueba'):
    flag = False
    if env == 'prueba':
        URL = WS_TEST_RECEIV
    else:
        URL = WS_RECEIV

    for i in [1, 2, 3]:
        try:
            res = requests.head(URL, timeout=3)
            flag = True
        except requests.exceptions.RequestException:
            return flag, False
    return flag, res
