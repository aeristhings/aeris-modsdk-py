class BaseShoulderTap:
    def __init__(self, payload, payloadId, imsi):
        '''Creates a representation of a Shoulder-Tap.
        Parameters
        ----------
        payload : bytes
            The payload contained by the shoulder-tap.
        payloadId : int or str
            The ID of the shoulder-tap, as present in its protocol representation.
        imsi : str
            The IMSI of this device.
        '''
        self.payload = payload
        self.payloadId = payloadId
        self.imsi = imsi

    def getRequestId(self):
        return self.payloadId


class Udp0ShoulderTap(BaseShoulderTap):
    def getRequestId(self):
        '''Returns the request ID of this shoulder-tap. It is formatted as this device's IMSI, a dash,
        and the sequence number (in base-10) from the payload. '''
        return f'{self.imsi}-{self.payloadId}'
