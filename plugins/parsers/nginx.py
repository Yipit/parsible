import re

def parse_nginx(line):
    regex = re.compile("(?P<ip_address>\S*)\s-\s(?P<requesting_user>\S*)\s\[(?P<timestamp>.*?)\]\s{1,2}\"(?P<method>\S*)\s*(?P<request>\S*)\s*(HTTP\/)*(?P<http_version>.*?)\"\s(?P<response_code>\d{3})\s(?P<size>\S*)\s\"(?P<referrer>[^\"]*)\"\s\"(?P<client>[^\"]*)\"\s(?P<service_time>\S*)\s(?P<application_time>\S*)\s(?P<pipe>\S*)")
    r = regex.search(line)
    result_set = {}
    if r:
        for k, v in r.groupdict().iteritems():
            if v is None or v is "-":
                continue
            if "request" in k:
                if "?" in v:
                    request = v.partition("?")
                    path = request[0]
                    query = request[2]
                    result_set["path"] = path
                    result_set["query"] = query
                    r.groupdict().pop(k)
                    continue
                else:
                    result_set["path"] = r.groupdict().pop(k)
                    continue
            result_set[k] = r.groupdict().pop(k)
    return result_set




