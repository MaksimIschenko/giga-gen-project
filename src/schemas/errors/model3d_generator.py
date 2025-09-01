""" Errors for Model3DGenerator """

from pydantic import BaseModel


class Model3DGeneratorError(BaseModel):
    """ Errors for Model3DGenerator """
    message: str