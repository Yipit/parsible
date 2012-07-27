from plugins.outputs.statsd import output_statsd_count

def process_ajax(line):
    if 'path' in line.keys():
        if line['path'].startswith('/ajax/'):
            output_statsd_count('call.ajax')

def process_api(line):
    if 'path' in line.keys():
        if line['path'].startswith('/api/'):
            output_statsd_count('call.api')

def process_os_and_user_agent_request(line):
    if 'client' in line.keys():
        user_agent, os = _get_platform(line['client'])
        metric_name = 'browser_request.{0}.{1}'.format(user_agent, os)
        output_statsd_count(metric_name)

def _get_platform(user_agent_string):
    user_agent_string = user_agent_string.lower()

    # Dumb parser to attempt to get a simple UA and OS
    user_agent = 'unknown'
    os = 'unknown'

    # Check IE and get version
    if 'msie' in user_agent_string:
        for ie_version in ['4','5','6', '7', '8', '9', '10']:
            if "msie {}".format(ie_version) in user_agent_string:
                user_agent = 'ie{}'.format(ie_version)

    # Check Webkit
    if 'safari' in user_agent_string:
        # Determine if Chrome or Safari
        if 'chrome' in user_agent_string:
            user_agent = 'chrome'
        else:
            user_agent = 'safari'

    # Check Firefox
    if 'firefox' in user_agent_string:
        user_agent = 'firefox'

    # Figure out OS
    if 'windows' in user_agent_string:
        os = 'windows'
    elif 'mac' in user_agent_string:
        os = 'mac'
    elif 'linux' in user_agent_string:
        os = 'linux'

    # Keep track of our bots
    for bot in ['bot', 'spider', 'symfony', 'grabber']:
        if bot in user_agent_string:
            user_agent = 'bot'
            os = 'bot'

    return (user_agent, os)