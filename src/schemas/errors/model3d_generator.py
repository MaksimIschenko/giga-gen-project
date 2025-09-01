""" Errors for Model3DGenerator """

from pydantic import BaseModel


class Model3DGeneratorError(BaseModel):
    """ Errors for Model3DGenerator """
    message: str
    
class Meshy3DError(RuntimeError):
    """ Errors for Meshy3D """


class Meshy3DProviderUnavailableError(Meshy3DError):
    """ Errors for Meshy3D Provider Unavailable """


class Meshy3DTimeoutError(Meshy3DError):
    """ Errors for Meshy3D Timeout """