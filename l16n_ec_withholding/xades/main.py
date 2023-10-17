import base64
from datetime import datetime

import xmlsig
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree

from base import parse_xml
from xades import template, utils, ObjectIdentifier, XAdESContext
from xades.policy import ImpliedPolicy


def exades_signed(document, path_p12, passwod):
    root = parse_xml(document)
    root = etree.fromstring(document)
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
        doc = ctx.sign(signature)

    doct_str = etree.tostring(root)
    signature_str = etree.tostring(signature)
    doct_str = b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>' + doct_str

    buffer_xml = base64.b64encode(doct_str)
    return buffer_xml
