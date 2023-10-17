# -*- coding: utf-8 -*-

import base64
from datetime import datetime

import xmlsig
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree

from .xades import template, utils, ObjectIdentifier, XAdESContext
from .xades.policy import ImpliedPolicy


class CheckDigit(object):
    # Definicion modulo 11
    _MODULO_11 = {
        'BASE': 11,
        'FACTOR': 2,
        'RETORNO11': 0,
        'RETORNO10': 1,
        'PESO': 2,
        'MAX_WEIGHT': 7
    }

    @classmethod
    def _eval_mod11(self, modulo):
        if modulo == self._MODULO_11['BASE']:
            return self._MODULO_11['RETORNO11']
        elif modulo == self._MODULO_11['BASE'] - 1:
            return self._MODULO_11['RETORNO10']
        else:
            return modulo

    @classmethod
    def compute_mod11(self, dato):
        """
        Calculo mod 11
        return int
        """
        total = 0
        weight = self._MODULO_11['PESO']

        for item in reversed(dato):
            total += int(item) * weight
            weight += 1
            if weight > self._MODULO_11['MAX_WEIGHT']:
                weight = self._MODULO_11['PESO']
        mod = 11 - total % self._MODULO_11['BASE']

        mod = self._eval_mod11(mod)
        return mod


class Xades(object):

    def sign(self, document, path_p12, passwod):

        root = etree.fromstring(document.encode('utf-8'))
        signature = xmlsig.template.create(
            xmlsig.constants.TransformInclC14N,
            xmlsig.constants.TransformRsaSha1,
            "Signature",
        )
        ref = xmlsig.template.add_reference(
            signature, xmlsig.constants.TransformSha1, uri="", name="R1"
        )
        xmlsig.template.add_transform(ref, xmlsig.constants.TransformEnveloped)
        xmlsig.template.add_reference(
            signature, xmlsig.constants.TransformSha1, uri="#KI", name="RKI"
        )
        ki = xmlsig.template.ensure_key_info(signature, name="KI")
        data = xmlsig.template.add_x509_data(ki)
        xmlsig.template.x509_data_add_certificate(data)
        serial = xmlsig.template.x509_data_add_issuer_serial(data)
        xmlsig.template.x509_issuer_serial_add_issuer_name(serial)
        xmlsig.template.x509_issuer_serial_add_serial_number(serial)
        xmlsig.template.add_key_value(ki)
        qualifying = template.create_qualifying_properties(signature)
        utils.ensure_id(qualifying)
        utils.ensure_id(qualifying)
        props = template.create_signed_properties(qualifying, datetime=datetime.now())
        template.add_claimed_role(props, "Supp")
        signed_do = template.ensure_signed_data_object_properties(props)
        template.add_data_object_format(
            signed_do, "#R1", identifier=ObjectIdentifier("Idenfitier0", "Description")
        )
        template.add_commitment_type_indication(
            signed_do,
            ObjectIdentifier("Idenfitier0", "Description"),
            qualifiers_type=["Tipo"],
        )

        template.add_commitment_type_indication(
            signed_do,
            ObjectIdentifier("Idenfitier1", references=["#R1"]),
            references=["#R1"],
        )
        template.add_data_object_format(
            signed_do,
            "#RKI",
            description="Desc",
            mime_type="application/xml",
            encoding="UTF-8",
        )
        root.append(signature)
        ctx = XAdESContext(ImpliedPolicy(xmlsig.constants.TransformSha1))
        with open(path_p12, "rb") as key_file:
            ctx.load_pkcs12(pkcs12.load_key_and_certificates(key_file.read(), passwod.encode('utf-8')))
            ctx.sign(signature)
            # ctx.verify(signature)

        doct_str = etree.tostring(root,pretty_print=True, xml_declaration=True)

        buffer_xml = base64.b64encode(doct_str)
        return False, buffer_xml
