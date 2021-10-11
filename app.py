#!/usr/local/bin/python3.9
import datetime
import os
import subprocess
import re
import logging
import configparser
import pytz
import rumps
# from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, SSHException, BadHostKeyException
# from scp import SCPClient, SCPException
# import scp
# import paramiko

CHECK_TIMER = 60
AWS_CREDENTIALS = f"{os.path.expanduser('~')}/.aws/credentials"
SSH_USER = None
SSH_HOST = None
SSH_KEY = None
SSH_PORT = 22


def load_config():
    """Load app config"""
    conf = configparser.ConfigParser()
    conf.sections()
    conf.read("./app.conf")
    if 'app' in conf:
        global SSH_USER
        global SSH_HOST
        global CHECK_TIMER
        global SSH_PORT
        global SSH_KEY
        if 'ssh_user' in conf['app']:
            SSH_USER = conf['app']['ssh_user']
        if 'ssh_host' in conf['app']:
            SSH_HOST = conf['app']['ssh_host']
        if 'ssh_port' in conf['app']:
            SSH_PORT = conf['app']['ssh_port']
        if 'ssh_key' in conf['app']:
            SSH_KEY = conf['app']['ssh_key']
        if 'check_timer' in conf['app']:
            CHECK_TIMER = conf['app']['check_timer']


class App(rumps.App):
    """App """
    def __init__(self):
        logs.debug("_init_")
        super(App, self).__init__("saml2aws")
        self.menu.add(rumps.MenuItem(title='TimeExp'))
        self.menu.add(rumps.MenuItem(title='TimeUntil'))
        self.menu.add(rumps.MenuItem(title='CurrRole'))
        self.menu.add(rumps.MenuItem(title='CheckTimer'))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem(title='AWS caller identity'))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem(title='Run saml2aws'))
        self.menu.add(rumps.MenuItem(title='Copy creds to JH'))
        self.menu.add(rumps.MenuItem(title='Refresh status'))
        # rumps.debug_mode(True)

    def get_creds(self):
        """Check token expiring"""
        creds = configparser.ConfigParser()
        creds.sections()
        if os.path.isfile(AWS_CREDENTIALS) is False:
            logs.error("No %s file", AWS_CREDENTIALS)
            return 0, 0, 0
        creds.read(AWS_CREDENTIALS)
        if "saml" not in creds:
            logs.error("No saml section in credentials")
            return 0, 0, 0
        if "x_security_token_expires" in creds['saml']:
            logs.debug("have_x")
            HAVE_X = True
            time_expiring = datetime.datetime.strptime(creds['saml']['x_security_token_expires'], "%Y-%m-%dT%H:%M:%S%z")
            r = time_expiring - datetime.datetime.now().astimezone(pytz.UTC)
            time_until = round(r.total_seconds() / 60, 0)
            logs.debug("have_x")
            if time_until <= 0:
                text = f"Expired {time_expiring.strftime('%Y-%m-%d %H:%M')}"
                # rumps.notification(title="saml2aws", subtitle="!!!!", message="Token time expired")
            elif time_until <= 10:
                text = f"*** {time_until} min ***\nUntil: {time_expiring.strftime('%H:%M')}"
                # rumps.notification(title="saml2aws", subtitle="!!!!", message="Token time expiring soon")
            else:
                text = f" {time_until} min\nUntil: {time_expiring.strftime('%H:%M')}"
                logs.debug(text)
                logs.debug(f"time_expiring: {time_expiring} time_until: {time_until}")
        if "x_principal_arn" in creds['saml']:
            result = re.search(r".*(\/.*\/).*$", creds['saml']['x_principal_arn'])
            logs.debug(f"role: {result.group(1)}")
            current_role = result.group(1)
        if not HAVE_X:
            logs.error("NO have_x")
            # rumps.alert("Invalid Saml")
        logs.debug(f"Ret {time_expiring} {time_until} {current_role}")
        return time_expiring, time_until, current_role

    def refresh_status(self):
        """Refresh expiring information on menu."""
        logs.debug("refresh_status")
        time_expiring, time_until, current_role = self.get_creds()
        self.menu['TimeExp'].title = f"Exp: {time_expiring}"
        self.menu['TimeUntil'].title = f"Until: {time_until} min"
        self.menu['CurrRole'].title = f"Role: {current_role}"
        self.menu['CheckTimer'].title = f"CheckTimer: {CHECK_TIMER} {datetime.datetime.now().strftime('%m-%d %H:%M:%S')}"
        self.title = ''.join(f"{time_until}")

    # @rumps.timer(60 * 60)
    @rumps.timer(CHECK_TIMER)
    def get_check_that(self, sender):
        """ Timer """
        logs.debug("Timer")
        logs.debug(rumps.timers())

        def counter(t):
            self.refresh_status()

        # if bind on clicked action
        # set_timer = rumps.Timer(callback=counter, interval=60 * 60)
        # set_timer.start()

        counter(None)

    @rumps.clicked("Refresh status")
    def call_refresh_status(self, _):
        """ Call refresh status """
        logs.debug("Call refresh status")
        self.refresh_status()

    @rumps.clicked("AWS caller identity")
    def get_aws_identity(self, _):
        """AWS caller identity"""
        logs.debug("AWS caller identity")
        creds = configparser.ConfigParser()
        creds.sections()
        if os.path.isfile(AWS_CREDENTIALS) is False:
            logs.error("No %s file", AWS_CREDENTIALS)
            return 0, 0, 0
        creds.read(AWS_CREDENTIALS)
        if "saml" not in creds:
            logs.error("No saml section in credentials")
            return 0, 0, 0
        if "x_principal_arn" in creds['saml']:
            result = re.search(r".*(\/.*\/).*$", creds['saml']['x_principal_arn'])
            logs.debug(f"role: {result.group(1)}")
            rumps.alert(f"Current role:\n {result.group(1)}")

    @rumps.clicked("Run saml2aws")
    def run_terminal(self, _):
        """Clear saml section and start terminal with saml2login command"""
        logs.debug("Run saml2login")
        p = configparser.ConfigParser()
        logs.debug("clear section")
        with open(AWS_CREDENTIALS, 'r+') as s:
            p.read_file(s)  # File position changed (it's at the end of the file)
            p.remove_section('saml')
            s.seek(0)  # <-- Change the file position to the beginning of the file
            p.write(s)
            s.truncate()  # <-- Truncate remaining content after the written position.
        logs.debug("run terminal")
        os.system("alacritty -e saml2aws login")

    @rumps.clicked("Copy creds to JH")
    def cp_creds(self, _):
        """Copy local creds to JH"""
        logs.debug("Copy creds to JH")
        if SSH_HOST is None or SSH_USER is None or SSH_KEY is None:
            logs.debug("SSH vars not set exiting")
            rumps.alert("saml", "SSH-Error", "Not set ssh vars in config")
            return
        try:
            scp = subprocess.Popen(['scp', '-P', SSH_PORT, '-i', SSH_KEY, AWS_CREDENTIALS, '{}@{}:{}'.format(SSH_USER, SSH_HOST, ".aws/credentials")])
            logs.debug(scp)
            rumps.notification(title="SAML", subtitle="SCP copy", message="Creds copied to JH")
        except subprocess.CalledProcessError:
            logs.debug("SCP error")
            rumps.alert("SCP Error")

#        with paramiko.SSHClient() as ssh:
#            logs.debug("ssh-connecting...")
#            ssh.load_system_host_keys()
#            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#            ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, key_filename=SSH_KEY, timeout=15)
#            logs.debug("ssh-connected")
#            with scp.SCPClient(ssh.get_transport()) as scpp:
#                logs.debug("scp")
#                scpp.put(AWS_CREDENTIALS, '.aws/credentials')


if __name__ == "__main__":
    print(os.environ.get("LOGLEVEL", "BLLL"))
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s -  %(message)s',
                        level=os.environ.get("LOGLEVEL", "ERROR"))
    logs = logging.getLogger()
    logs.info("Starting")
    load_config()
    myapp = App()
    myapp.run()
