# Energy Monitoring Prompt Template

## Overview
This prompt template focuses on energy monitoring and management for smart homes, providing real-time insights and recommendations for energy efficiency.

## Energy Monitoring Focus
- **Real-time consumption tracking** from grid and local sources
- **Electric vehicle charging management** and optimization
- **Solar panel and battery storage monitoring**
- **Cost-aware recommendations** based on current electricity prices
- **Peak usage identification** and load balancing suggestions

## Key Energy Metrics
```
Electricity price now: {{ states('sensor.electricity_price_main_street') | round(2) | replace('.', ',') }} kr
Grid consumption: {{ (states('sensor.shelly_3em_house_consumption_total_active_power') | float / 1000) | round(2) | replace('.', ',') }} kW

EV Charger 1: {{ (states('sensor.main_street_charger_2109013766a_1_power') | float / 1000) | round(2) | replace('.', ',') }} kW
EV Charger 2: {{ (states('sensor.main_street_charger_2109013766a_2_power') | float / 1000) | round(2) | replace('.', ',') }} kW

Battery status: {{ states('sensor.audi_q8_e_tron_state_of_charge') }}% charged
```

## Price Thresholds
- **Under 0.5 kr/kWh**: Optimal for high consumption activities
- **0.5-1.0 kr/kWh**: Normal pricing, moderate consumption
- **1.0-2.0 kr/kWh**: High pricing, reduce non-essential usage
- **Over 2.0 kr/kWh**: Very high pricing, minimize consumption
- **Over 3.0 kr/kWh**: Extreme pricing, essential usage only

## Seasonal Energy Patterns
- **Fall/Winter/Spring**: Higher consumption due to heat pump operation
- **Summer**: Lower consumption, potential solar surplus
- **Peak periods**: Often coincide with EV charging sessions

## Smart Recommendations
- **Load shifting** to low-price periods
- **EV charging optimization** during cheap electricity hours
- **Battery storage utilization** during peak pricing
- **Solar panel monitoring** for self-consumption optimization

## Usage Examples
```
# Check current energy status
"Show me the current energy consumption and pricing"

# Optimize EV charging
"When is the cheapest time to charge the electric vehicles today?"

# Monitor solar production
"How much solar energy are we generating right now?"

# Energy cost analysis
"What will today's energy consumption cost us?"
```

## Integration Points
- **Grid consumption sensors** for real-time monitoring
- **EV charger power meters** for vehicle charging tracking
- **Solar panel inverters** for renewable energy monitoring
- **Battery storage systems** for energy storage optimization
- **Smart thermostats** for heating efficiency

## Alert Conditions
- **High consumption** during expensive periods
- **Peak load warnings** when approaching capacity limits
- **Solar panel issues** when production drops unexpectedly
- **Battery storage problems** when charge levels are low
- **EV charging conflicts** when multiple vehicles charge simultaneously
