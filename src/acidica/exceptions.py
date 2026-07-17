class AcidicaError(Exception):
    def __init__(self, msg):
        super().__init__(f"!{msg}")
