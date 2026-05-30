import math
import random


class Turbine:
    """
    Simulated wind turbine modelled on the Enercon E-82 (2 MW, 82m rotor).

    Power curve behaviour:
      - Below cut-in (3 m/s): 0 W, not enough wind
      - Cut-in to rated (3-12 m/s): power increases with cube of wind speed
      - At and above rated (12 m/s): capped at nameplate rated_power
      - Above cut-out (25 m/s): 0 W, turbine shuts down for safety

    Physics model uses the Betz formula for the ramp-up region.
    Rated power is a fixed design parameter, not calculated - this matches
    how real turbines work (blades pitch to shed excess wind above rated speed).
    """

# NOTE: Cp is treated as constant here. Real turbines have a Cp curve
# that varies with tip‑speed ratio and blade pitch. For a portfolio
# demo, constant Cp captures the correct cubic growth behaviour.

    def __init__(
        self,
        rotor_diameter: float = 82.0,
        rated_power: float = 2_000_000,  # Watts (2 MW nameplate)
        cp: float = 0.35,
        air_density: float = 1.225,
    ):
        # Immutable physical parameters
        self.rotor_diameter = rotor_diameter
        self.rotor_area = math.pi * (rotor_diameter / 2) ** 2
        self.rated_power = rated_power  # nameplate capacity in Watts
        self.cp = cp                    # power coefficient
        self.air_density = air_density  # kg/m³ at sea level

        # Mutable state (updated each timestep)
        self.wind_speed: float = 0.0
        self.power_output: float = 0.0
        self.rpm: int = 0
        self.temperature: float = 20.0

    def calculate_power(self, wind_speed: float) -> float:
        """
        Simplified power curve with three regions:
          1. Below cut-in or above cut-out → 0 W
          2. Cut-in to rated speed → Betz formula (cubic ramp)
          3. At or above rated speed → fixed at rated_power

        Rated power is the turbine's nameplate capacity (design spec),
        not derived from the formula. Real turbines pitch blades to
        maintain constant output above rated wind speed.
        """
        CUT_IN = 3.0    # m/s - minimum operating wind speed
        RATED = 12.0    # m/s - wind speed where full power is reached
        CUT_OUT = 25.0  # m/s - shutdown speed for safety

        if wind_speed < CUT_IN or wind_speed > CUT_OUT:
            return 0.0
        elif wind_speed < RATED:
            # Ramping up: power grows with cube of wind speed
            power = 0.5 * self.air_density * self.rotor_area * self.cp * (wind_speed ** 3)
            return round(power, 2)
        else:
            # At or above rated: capped at nameplate capacity
            return self.rated_power

    def calculate_rpm(self, wind_speed: float) -> int:
        """
        PLACEHOLDER: linear approximation of rotor RPM.
        Real RPM depends on blade pitch control and gear ratio.
        """
        return int(wind_speed * 8)

    def update(self, wind_speed: float) -> dict:
        """Simulate one timestep. Returns current turbine state."""
        # Add sensor noise (real sensors have measurement variance)
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
