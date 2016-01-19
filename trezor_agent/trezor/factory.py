''' Thin wrapper around trezor/keepkey libraries. '''
import binascii
import collections
import logging

import semver

log = logging.getLogger(__name__)

ClientWrapper = collections.namedtuple(
    'ClientWrapper',
    ['connection', 'identity_type', 'device_name'])


# pylint: disable=too-many-arguments
def _load_client(name, client_type, hid_transport,
                 passphrase_ack, identity_type, required_version):

    def empty_passphrase_handler(_):
        return passphrase_ack(passphrase='')

    for d in hid_transport.enumerate():
        connection = client_type(hid_transport(d))
        connection.callback_PassphraseRequest = empty_passphrase_handler
        f = connection.features
        log.debug('connected to %s %s', name, f.device_id)
        log.debug('label    : %s', f.label)
        log.debug('vendor   : %s', f.vendor)
        current_version = '{}.{}.{}'.format(f.major_version,
                                            f.minor_version,
                                            f.patch_version)
        log.debug('version  : %s', current_version)
        log.debug('revision : %s', binascii.hexlify(f.revision))
        if not semver.match(current_version, required_version):
            fmt = 'Please upgrade your {} firmware to {} version (current: {})'
            raise ValueError(fmt.format(name,
                                        required_version,
                                        current_version))
        yield ClientWrapper(connection=connection,
                            identity_type=identity_type,
                            device_name=name)


def _load_trezor():
    # pylint: disable=import-error
    from trezorlib.client import TrezorClient
    from trezorlib.transport_hid import HidTransport
    from trezorlib.messages_pb2 import PassphraseAck
    from trezorlib.types_pb2 import IdentityType
    return _load_client(name='Trezor',
                        client_type=TrezorClient,
                        hid_transport=HidTransport,
                        passphrase_ack=PassphraseAck,
                        identity_type=IdentityType,
                        required_version='>=1.3.4')


def _load_keepkey():
    # pylint: disable=import-error
    from keepkeylib.client import KeepKeyClient
    from keepkeylib.transport_hid import HidTransport
    from keepkeylib.messages_pb2 import PassphraseAck
    from keepkeylib.types_pb2 import IdentityType
    return _load_client(name='KeepKey',
                        client_type=KeepKeyClient,
                        hid_transport=HidTransport,
                        passphrase_ack=PassphraseAck,
                        identity_type=IdentityType,
                        required_version='>=1.0.4')

LOADERS = [
    _load_trezor,
    _load_keepkey
]


def load(loaders=None):
    loaders = loaders if loaders is not None else LOADERS
    device_list = []
    for loader in loaders:
        device_list.extend(loader())

    if len(device_list) == 1:
        return device_list[0]

    msg = '{:d} devices found'.format(len(device_list))
    raise IOError(msg)
