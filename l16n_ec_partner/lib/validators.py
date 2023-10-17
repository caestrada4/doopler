
def validate_cedula(nro):
    try:
        l = len(nro)
        if l == 10:  # verificar la longitud correcta
            list_cedula = list(nro)
            list_val2 = []
            list_val3 = []
            list_val2.append(int(list_cedula[0]) * 2)
            list_val2.append(int(list_cedula[2]) * 2)
            list_val2.append(int(list_cedula[4]) * 2)
            list_val2.append(int(list_cedula[6]) * 2)
            list_val2.append(int(list_cedula[8]) * 2)
            # lista 3
            list_val3.append(list_val2[0] if list_val2[0] < 9 else list_val2[0] - 9)
            list_val3.append(int(list_cedula[1]))
            list_val3.append(list_val2[1] if list_val2[1] < 9 else list_val2[1] - 9)
            list_val3.append(int(list_cedula[3]))
            list_val3.append(list_val2[2] if list_val2[2] < 9 else list_val2[2] - 9)
            list_val3.append(int(list_cedula[5]))
            list_val3.append(list_val2[3] if list_val2[3] < 9 else list_val2[3] - 9)
            list_val3.append(int(list_cedula[7]))
            list_val3.append(list_val2[4] if list_val2[4] < 9 else list_val2[4] - 9)


            pares = int(list_val3[1]) + int(list_val3[3]) + int(list_val3[5]) + int(list_val3[7])
            impar = int(list_val3[0]) + int(list_val3[2]) + int(list_val3[4]) + int(list_val3[6]) + int(list_val3[8])
            total = pares + impar
            mt10 = str(total)[-1]
            dig_verificador = 0
            if int(list_cedula[9]) == 0:
                dig_verificador = 0
            else:
                dig_verificador = 10 - int(mt10)
            if dig_verificador == int(list_cedula[9]):
                return True
            return False

        else:
            return False
    except:
        return False



def validate_ruc (nro):
    try:
        l = len(nro)
        if l == 13:  # verificar la longitud correcta
            cp = int(nro[0:2])
            if cp >= 1 and cp <= 22:  # verificar codigo de provincia
                tercer_dig = int(nro[2])
                if tercer_dig >= 0 and tercer_dig < 6:  # numeros enter 0 y 6
                    if l == 10:
                        return __validar_ced_ruc(nro, 0)
                    elif l == 13:
                        return __validar_ced_ruc(nro, 0) and nro[10:13] != '000'
                elif tercer_dig == 6:
                    return __validar_ced_ruc(nro, 1)  # sociedades publicas
                elif tercer_dig == 9:  # si es ruc
                    return __validar_ced_ruc(nro, 2)  # sociedades privadas
                else:
                    return False
            else:
                return False
        else:
            return False
    except:
        return False

def __validar_ced_ruc(nro, tipo):
    total = 0
    if tipo == 0:  # cedula y r.u.c persona natural
        base = 10
        d_ver = int(nro[9])  # digito verificador
        multip = (2, 1, 2, 1, 2, 1, 2, 1, 2)
    elif tipo == 1:  # r.u.c. publicos
        base = 11
        d_ver = int(nro[8])
        multip = (3, 2, 7, 6, 5, 4, 3, 2)
    elif tipo == 2:  # r.u.c. juridicos y extranjeros sin cedula
        base = 11
        d_ver = int(nro[9])
        multip = (4, 3, 2, 7, 6, 5, 4, 3, 2)
    for i in range(0, len(multip)):
        p = int(nro[i]) * multip[i]
        if tipo == 0:
            total += p if p < 10 else int(str(p)[0] ) +int(str(p)[1])
        else:
            total += p
    mod = total % base
    val = base - mod if mod != 0 else 0
    return val == d_ver
