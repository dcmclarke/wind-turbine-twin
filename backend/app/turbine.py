import math
import random


class Turbine:
    """
    Simulated wind turbine using the theoretical Betz formula:
        P = 0.5 × rho × A × Cp × v³

    Real turbines use empirical power curves from manufacturer data.
    This simplified model can be swapped for windpowerlib curves later.
    """

    def __init__(self, rotor_diameter: float = 80.0, cp: float = 0.35):
        # Immutable physical parameters
        self.rotor_diameter = rotor_diameter
        self.rotor_area = math.pi * (rotor_diameter / 2) ** 2
        self.cp = cp               # Power coefficient (max theoretical: 0.59)
        self.air_density = 1.225   # kg/m³ at sea level

        # Mutable state (updated each timestep)
        self.wind_speed: float = 0.0
        self.power_output: float = 0.0
        self.rpm: int = 0
        self.temperature: float = 20.0  # Celsius

    def calculate_power(self, wind_speed: float) -> float:
        """
        Betz formula: P = 0.5 × rho × A × Cp × v³
        Returns 0 outside operational wind speed range.
        """
        CUT_IN = 3.0    # Turbine starts at 3 m/s
        CUT_OUT = 25.0  # Turbine shuts off above 25 m/s (safety)

        if wind_speed < CUT_IN or wind_speed > CUT_OUT:
            return 0.0

        power = 0.5 * self.air_density * self.rotor_area * self.cp * (wind_speed ** 3)
        return round(power, 2)

    def calculate_rpm(self, wind_speed: float) -> int:
        """
        PLACEHOLDER: linear approximation of rotor RPM.
        Real RPM depends on blade pitch control and gear ratio.
        """
        return int(wind_speed * 8)

    def update(self, wind_speed: float) -> dict:
        """Simulate one timestep. Returns current turbine state."""
        # Add sensor noise (real sensors aren't perfect)
        noisy_wind = max(0.0, wind_speed + random.gauss(0, 0.2))

        self.wind_speed = round(noisy_wind, 2)
        self.power_output = self.calculate_power(self.wind_speed)
        self.rpm = self.calculate_rpm(self.wind_speed)

        # PLACEHOLDER: demo heating only, not physically accurate
        self.temperature = round(self.temperature + (self.power_output * 0.000001), 2)

        return {
            "wind_speed": self.wind_speed,
            "power_output": self.power_output,
            "rpm": self.rpm,
            "temperature": self.temperature,
        }
