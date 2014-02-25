import re

def parse_proftpd_xfrlog(line):
    rtrnobj = {}
    regex = re.compile("((?:\w+\s){3}(?:\d+:\d+){2}\s\d{4}).*\d\s/([\x21-\x7E]+ *[\x21-\x7E]+) [ba] [CUT_] ([oid]) [agr] ([\w\-_]+)(\s\w+)\s([01])\s([\*\w])\s([ci])")
    matchobj = regex.search(line)
    if matchobj:
        rtrnobj["date"] = matchobj.group(1)
        rtrnobj["filename"] = matchobj.group(2)
        rtrnobj["direction"] = matchobj.group(3)
        rtrnobj["username"] = matchobj.group(4)
        rtrnobj["servicename"] = matchobj.group(5)
        if matchobj.group(6) == "0":
            rtrnobj["authmethod"] = "none"
        else:
            rtrnobj["authmethod"] = "RFC931"

        rtrnobj["authenticateduid"] = matchobj.group(7)

        if matchobj.group(8) == "c":
            rtrnobj["completed"] = True
        else:
            rtrnobj["completed"] = False

    return rtrnobj
