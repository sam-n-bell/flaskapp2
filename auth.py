import jwt

from jwt.contrib.algorithms.pycrypto import RSAAlgorithm
from jwt.contrib.algorithms.py_ecdsa import ECAlgorithm

# comment these two lines out for deploying on Google
# jwt.unregister_algorithm('RS256')
# jwt.unregister_algorithm('ES256')

jwt.register_algorithm('RS256', RSAAlgorithm(RSAAlgorithm.SHA256))
jwt.register_algorithm('ES256', ECAlgorithm(ECAlgorithm.SHA256))


def create_token(user_dict):
    encoded = jwt.encode(user_dict, 'secret')
    return encoded


def decode_token(header):
    print(header)
    if header.split(' ')[0] != 'Bearer':
        raise Exception('Auth header needed')
    decoded = jwt.decode(header.split(' ')[1], 'secret')
    return decoded
