from plugins.outputs.statsd import output_statsd_count

def process_ajax(line):
    if line['request'].startswith('/ajax/'):
        output_statsd_count('ajax')

def process_api(line):
    if line['request'].startswith('/api/'):
        output_statsd_count('api')

def process_business(line):
    if line['request'].startswith('/business/'):
        output_statsd_count('business')
