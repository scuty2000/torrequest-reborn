import stem
from stem.control import Controller
from stem.process import launch_tor_with_config

import requests

import time

import socket

class TorRequest(object):
  def __init__(self, password=None):

    self.proxy_port, self.ctrl_port = self.choose_tor_ports()

    self._tor_proc = None
    if not self._tor_process_exists():
      self._tor_proc = self._launch_tor()

    self.ctrl = Controller.from_port(port=self.ctrl_port)
    self.ctrl.authenticate(password=password)

    self.session = requests.Session()
    self.session.proxies.update({
      'http': 'socks5://localhost:%d' % self.proxy_port,
      'https:': 'socks5://localhost:%d' % self.proxy_port,
    })


  # Default port is in use, use auxiliary ports
  def choose_tor_ports(self):
    if self.is_port_in_use(9050):

       proxy_port = 9052
       ctrl_port = 9053
    else:
  # Default port is not in use, use TorRequest default ports
       proxy_port = 9050
       ctrl_port = 9051

    return proxy_port, ctrl_port

  def is_port_in_use(self, port):
       try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(('127.0.0.1', port))
                return True
       except (socket.timeout, ConnectionRefusedError):
           return False

       self.session.proxies.update({
          'https': 'socks5h://localhost:%d' % self.proxy_port,
    })

  def _tor_process_exists(self):
    try:
      ctrl = Controller.from_port(port=self.ctrl_port)
      ctrl.close()
      return True
    except:
      return False

  def _launch_tor(self):
    return launch_tor_with_config(
      config={
        'SocksPort': str(self.proxy_port),
        'ControlPort': str(self.ctrl_port)
      },
      take_ownership=True)

  def close(self):
    try:
      self.session.close()
    except: pass

    try:
      self.ctrl.close()
    except: pass

    if self._tor_proc:
      self._tor_proc.terminate()

  #Fix identity change (session renewal) and HTTPs proxies not using tor
  def reset_identity_async(self):
    self.ctrl.signal(stem.Signal.NEWNYM)

  def _reset_session(self):
    self.session = requests.Session()
    self.session.proxies.update({
        'http': 'socks5://localhost:%d' % self.proxy_port,
        'https': 'socks5://localhost:%d' % self.proxy_port,
    })

  def reset_identity(self):
    self._reset_session()
    self.reset_identity_async()
    time.sleep(self.ctrl.get_newnym_wait())

  def get(self, *args, **kwargs):
    return self.session.get(*args, **kwargs)

  def post(self, *args, **kwargs):
    return self.session.post(*args, **kwargs)

  def put(self, *args, **kwargs):
    return self.session.put(*args, **kwargs)

  def patch(self, *args, **kwargs):
    return self.session.patch(*args, **kwargs)

  def delete(self, *args, **kwargs):
    return self.session.delete(*args, **kwargs)

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()
