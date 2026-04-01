from inspect import signature

def move_toolhead(x: float, y: float, z: float, relative: int):
    pass

def move_to_location(destination: str):
    pass

def measure_spectrum(measurement_type: str):
    pass

def set_finger_angle(angle:int):
    pass

for f in [move_toolhead, move_to_location, measure_spectrum, set_finger_angle]:
    sig = signature(f)
    params = list(sig.parameters.values())
    if params and params[0].name == 'self':
        params = params[1:]
    names = [p.name for p in params]
    print(f.__name__, 'params ->', names)
    # build default args
    default_args = []
    for i,p in enumerate(params):
        if p.default is not p.empty:
            default_args.append(p.default)
        elif f.__name__ == 'move_to_location' and i == 0:
            default_args.append('SLIDEMAT1')
        else:
            default_args.append(0)
    print(' defaults ->', default_args)
