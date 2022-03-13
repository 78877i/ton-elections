import base64
import crc16
import json


def dec2hex(dec):
    h = hex(dec)[2:]
    if len(h) % 2 > 0:
        h = '0' + h
    return h

# Ref: https://github.com/ton-blockchain/mytonctrl/blob/f84dae39353766c8524733594a83cc7e0c6c71d3/mytoncore.py#L3236
def Dec2HexAddr(dec):
    h = dec2hex(dec)
    hu = h.upper()
    h64 = hu.rjust(64, "0")
    return h64

# Ref: https://github.com/igroman787/mypylib/blob/447655f4485181da6978f0d41b33a82d4861713f/mypylib.py#L647
def Pars(text, search, search2=None):
    if search is None or text is None:
        return None
    if search not in text:
        return None
    text = text[text.find(search) + len(search):]
    if search2 is not None and search2 in text:
        text = text[:text.find(search2)]
    return text

# Ref: https://github.com/ton-blockchain/mytonctrl/blob/cf14be114ca4bcffa1d1280550c0951310c86fef/mytoncore.py#L2651
def Tlb2Json(text):
    # Заменить скобки
    start = 0
    end = len(text)
    if '=' in text:
        start = text.find('=')+1
    if "x{" in text:
        end = text.find("x{")
    text = text[start:end]
    text = text.strip()
    text = text.replace('(', '{')
    text = text.replace(')', '}')

    # Добавить кавычки к строкам (1 этап)
    buff = text
    buff = buff.replace('\r', ' ')
    buff = buff.replace('\n', ' ')
    buff = buff.replace('\t', ' ')
    buff = buff.replace('{', ' ')
    buff = buff.replace('}', ' ')
    buff = buff.replace(':', ' ')

    # Добавить кавычки к строкам (2 этап)
    buff2 = ""
    itemList = list()
    for item in list(buff):
        if item == ' ':
            if len(buff2) > 0:
                itemList.append(buff2)
                buff2 = ""
            itemList.append(item)
        else:
            buff2 += item
    #end for

    # Добавить кавычки к строкам (3 этап)
    i = 0
    for item in itemList:
        l = len(item)
        if item == ' ':
            pass
        elif item.isdigit() is False:
            c = '"'
            item2 = c + item + c
            text = text[:i] + item2 + text[i+l:]
            i += 2
        #end if
        i += l
    #end for

    # Обозначить тип объекта
    text = text.replace('{"', '{"_":"')

    # Расставить запятые
    while True:
        try:
            data = json.loads(text)
            break
        except json.JSONDecodeError as err:
            if "Expecting ',' delimiter" in err.msg:
                text = text[:err.pos] + ',' + text[err.pos:]
            elif "Expecting property name enclosed in double quotes" in err.msg:
                text = text[:err.pos] + '"_":' + text[err.pos:]
            else:
                raise err
    #end while

    return data
#end define

# Ref: https://github.com/ton-blockchain/mytonctrl/blob/69f0c57d4797db0621ab2f0b24af0420a427aeed/mytoncore.py#L2302
def Result2List(text):
    buff = Pars(text, "result:", "\n")
    if buff is None or "error" in buff:
        return
    buff = buff.replace(')', ']')
    buff = buff.replace('(', '[')
    buff = buff.replace(']', ' ] ')
    buff = buff.replace('[', ' [ ')
    arr = buff.split()

    # Get good raw data
    output = ""
    arrLen = len(arr)
    for i in range(arrLen):
        item = arr[i]
        # get next item
        if i+1 < arrLen:
            nextItem = arr[i+1]
        else:
            nextItem = None
        # add item to output
        if item == '[':
            output += item
        elif nextItem == ']':
            output += item
        elif '{' in item or '}' in item:
            output += "\"{item}\", ".format(item=item)
        elif i+1 == arrLen:
            output += item
        else:
            output += item + ', '
    #end for
    data = json.loads(output)
    return data
#end define

# Ref: https://github.com/ton-blockchain/mytonctrl/blob/f84dae39353766c8524733594a83cc7e0c6c71d3/mytoncore.py#L2534
def HexAddr2Base64Addr(fullAddr, bounceable=True, testnet=False):
    buff = fullAddr.split(':')
    workchain = int(buff[0])
    addr_hex = buff[1]
    if len(addr_hex) != 64:
        raise Exception("HexAddr2Base64Addr error: Invalid length of hexadecimal address")
    #end if

    # Create base64 address
    b = bytearray(36)
    b[0] = 0x51 - bounceable * 0x40 + testnet * 0x80
    b[1] = workchain % 256
    b[2:34] = bytearray.fromhex(addr_hex)
    buff = bytes(b[:34])
    crc = crc16.crc16xmodem(buff)
    b[34] = crc >> 8
    b[35] = crc & 0xff
    result = base64.b64encode(b)
    result = result.decode()
    result = result.replace('+', '-')
    result = result.replace('/', '_')
    return result
#end define