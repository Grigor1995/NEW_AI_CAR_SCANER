# Engineering units

The pure conversion function supports km/h↔mph, km↔mi, C↔F, kPa↔bar↔psi, Nm↔lb-ft, kW↔mechanical hp, L↔US gallon, cc↔engine liters, g/s↔lb/min and reciprocal L/100km↔km/L↔US/UK mpg. Nonfinite input, incompatible dimensions and zero/negative reciprocal fuel values are rejected. Conversion round trips and physical reference values are tested.

ECU measurements remain in native units; the UI converts valid speed and temperature at presentation boundaries only, without mutating raw values. Electrical volts/amps and RPM retain their engineering units. Fuel/pressure/torque/power selectors are not exposed in the current three-PID UI. No cumulative rounding or invented unsupported measurement is allowed.
