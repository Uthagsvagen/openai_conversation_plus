# Energy Monitoring Agent Example

## Overview
This agent continuously monitors energy consumption, costs, and efficiency to provide insights and automated responses for energy optimization.

## Agent Configuration

```yaml
agent:
  name: "Energy Monitor Agent"
  type: "monitoring"
  enabled: true
  schedule: "continuous"
  priority: "high"
  
  description: |
    Monitors energy consumption, costs, and efficiency.
    Provides alerts for high costs and usage spikes.
    Suggests optimization strategies.
```

## Data Sources

### Primary Sensors
```yaml
data_sources:
  electricity_price:
    entity: "sensor.electricity_price_main_street"
    description: "Current electricity price per kWh"
    unit: "kr/kWh"
    
  house_consumption:
    entity: "sensor.shelly_3em_house_consumption_total_active_power"
    description: "Total house power consumption"
    unit: "W"
    
  solar_production:
    entity: "sensor.solar_production_power"
    description: "Solar panel power production"
    unit: "W"
    
  battery_level:
    entity: "sensor.battery_storage_level"
    description: "Battery storage charge level"
    unit: "%"
    
  ev_charger_1:
    entity: "sensor.main_street_charger_2109013766a_1_power"
    description: "EV Charger 1 power consumption"
    unit: "W"
    
  ev_charger_2:
    entity: "sensor.main_street_charger_2109013766a_2_power"
    description: "EV Charger 2 power consumption"
    unit: "W"
```

## Monitoring Rules

### Price Thresholds
```yaml
price_rules:
  - name: "Very Cheap"
    condition: "price < 0.5"
    action: "encourage_high_usage"
    priority: "low"
    
  - name: "Cheap"
    condition: "0.5 <= price < 1.0"
    action: "normal_usage"
    priority: "low"
    
  - name: "Expensive"
    condition: "1.0 <= price < 2.0"
    action: "reduce_usage"
    priority: "medium"
    
  - name: "Very Expensive"
    condition: "2.0 <= price < 3.0"
    action: "minimize_usage"
    priority: "high"
    
  - name: "Extremely Expensive"
    condition: "price >= 3.0"
    action: "emergency_conservation"
    priority: "critical"
```

### Usage Patterns
```yaml
usage_rules:
  - name: "Normal Usage"
    condition: "consumption < 3000"
    action: "no_action"
    priority: "low"
    
  - name: "High Usage"
    condition: "3000 <= consumption < 5000"
    action: "monitor_closely"
    priority: "medium"
    
  - name: "Peak Usage"
    condition: "5000 <= consumption < 8000"
    action: "optimize_usage"
    priority: "high"
    
  - name: "Critical Usage"
    condition: "consumption >= 8000"
    action: "emergency_reduction"
    priority: "critical"
```

## Trigger Conditions

### Time-Based Triggers
```yaml
time_triggers:
  - name: "Morning Analysis"
    time: "07:00"
    action: "daily_energy_report"
    
  - name: "Evening Optimization"
    time: "18:00"
    action: "evening_usage_optimization"
    
  - name: "Night Mode"
    time: "22:00"
    action: "night_energy_conservation"
    
  - name: "Midnight Reset"
    time: "00:00"
    action: "daily_stats_reset"
```

### Event-Based Triggers
```yaml
event_triggers:
  - name: "Price Change"
    condition: "electricity_price_changed"
    threshold: 0.1  # 10% change
    action: "price_change_response"
    
  - name: "Usage Spike"
    condition: "consumption_increased"
    threshold: 2000  # 2kW increase
    action: "usage_spike_response"
    
  - name: "Solar Production Start"
    condition: "solar_production > 0"
    action: "solar_optimization"
    
  - name: "Battery Low"
    condition: "battery_level < 20"
    action: "battery_conservation"
```

## Automated Actions

### Notifications
```yaml
notifications:
  - name: "High Cost Alert"
    trigger: "price_threshold"
    service: "notify.mobile_app"
    data:
      title: "⚡ High Electricity Cost"
      message: |
        Current price: {{ states('sensor.electricity_price_main_street') }} kr/kWh
        This is {{ price_category }} pricing.
        Consider reducing usage until prices drop.
      priority: "high"
      
  - name: "Usage Spike Alert"
    trigger: "usage_spike"
    service: "notify.mobile_app"
    data:
      title: "🔌 High Energy Usage"
      message: |
        Current consumption: {{ states('sensor.shelly_3em_house_consumption_total_active_power') | float / 1000 | round(2) }} kW
        This is {{ usage_category }} usage.
        Check for unnecessary devices running.
      priority: "medium"
      
  - name: "Daily Energy Report"
    trigger: "morning_analysis"
    service: "notify.mobile_app"
    data:
      title: "📊 Daily Energy Report"
      message: |
        Yesterday's consumption: {{ daily_consumption }} kWh
        Cost: {{ daily_cost }} kr
        Efficiency: {{ efficiency_score }}%
        Recommendations: {{ recommendations }}
      priority: "low"
```

### Service Calls
```yaml
service_actions:
  - name: "Optimize Energy Usage"
    trigger: "high_usage"
    service: "script.optimize_energy_usage"
    data:
      target_reduction: 20
      priority_devices: ["lighting", "climate"]
      duration: 3600  # 1 hour
      
  - name: "Activate Solar Optimization"
    trigger: "solar_production_start"
    service: "script.solar_optimization"
    data:
      charge_battery: true
      activate_high_usage_devices: true
      priority: "high"
      
  - name: "Emergency Conservation"
    trigger: "critical_usage"
    service: "script.emergency_energy_conservation"
    data:
      reduce_lighting: 50
      adjust_climate: -2
      disable_non_essential: true
      duration: 1800  # 30 minutes
```

## Data Analysis

### Real-Time Calculations
```yaml
calculations:
  - name: "Current Cost per Hour"
    formula: "consumption_watts * price_kr_kwh / 1000"
    update_frequency: "1 minute"
    
  - name: "Daily Cost Projection"
    formula: "current_hourly_cost * 24"
    update_frequency: "1 hour"
    
  - name: "Efficiency Score"
    formula: "(solar_production / total_consumption) * 100"
    update_frequency: "5 minutes"
    
  - name: "Cost Savings"
    formula: "baseline_cost - current_cost"
    update_frequency: "1 hour"
```

### Historical Analysis
```yaml
historical_analysis:
  - name: "Weekly Trends"
    period: "7 days"
    metrics: ["consumption", "cost", "efficiency"]
    analysis: "trend_analysis"
    
  - name: "Monthly Comparison"
    period: "30 days"
    metrics: ["total_consumption", "total_cost", "peak_usage"]
    analysis: "monthly_comparison"
    
  - name: "Seasonal Patterns"
    period: "90 days"
    metrics: ["daily_patterns", "weather_correlation"]
    analysis: "seasonal_analysis"
```

## Optimization Strategies

### Load Shifting
```yaml
load_shifting:
  - name: "EV Charging Optimization"
    strategy: "charge_during_cheap_hours"
    conditions:
      - "price < 0.8"
      - "battery_level < 80"
    actions:
      - "enable_ev_charging"
      - "set_charging_power_max"
      
  - name: "Battery Storage Optimization"
    strategy: "store_cheap_energy"
    conditions:
      - "price < 0.6"
      - "solar_production = 0"
    actions:
      - "charge_battery_from_grid"
      - "set_charge_rate_optimal"
      
  - name: "High Usage Device Scheduling"
    strategy: "schedule_during_cheap_hours"
    devices: ["dishwasher", "washing_machine", "dryer"]
    conditions:
      - "price < 1.0"
      - "time_between 22:00-06:00"
    actions:
      - "schedule_device_operation"
      - "notify_user_of_schedule"
```

### Usage Reduction
```yaml
usage_reduction:
  - name: "Lighting Optimization"
    strategy: "reduce_lighting_during_peak"
    conditions:
      - "price > 1.5"
      - "time_between 17:00-22:00"
    actions:
      - "dim_lights_to_70_percent"
      - "turn_off_non_essential_lights"
      
  - name: "Climate Optimization"
    strategy: "adjust_climate_for_efficiency"
    conditions:
      - "price > 2.0"
      - "occupancy = low"
    actions:
      - "reduce_heating_by_2_degrees"
      - "enable_eco_mode"
      - "notify_user_of_changes"
```

## Performance Metrics

### Key Performance Indicators
```yaml
kpis:
  - name: "Cost Efficiency"
    metric: "cost_per_kwh_average"
    target: "< 1.0 kr/kWh"
    calculation: "total_cost / total_consumption"
    
  - name: "Usage Efficiency"
    metric: "consumption_per_person"
    target: "< 10 kWh/person/day"
    calculation: "daily_consumption / household_size"
    
  - name: "Solar Utilization"
    metric: "solar_self_consumption"
    target: "> 80%"
    calculation: "solar_used / solar_produced"
    
  - name: "Response Time"
    metric: "alert_response_time"
    target: "< 5 minutes"
    calculation: "time_from_trigger_to_action"
```

### Monitoring Dashboard
```yaml
dashboard:
  - name: "Real-Time Energy"
    widgets:
      - "current_consumption_gauge"
      - "current_price_display"
      - "efficiency_score"
      - "cost_per_hour"
      
  - name: "Daily Overview"
    widgets:
      - "daily_consumption_chart"
      - "cost_trend_line"
      - "usage_by_device_pie"
      - "optimization_suggestions"
      
  - name: "Historical Analysis"
    widgets:
      - "weekly_trends_chart"
      - "monthly_comparison"
      - "seasonal_patterns"
      - "cost_savings_tracker"
```

## Testing and Validation

### Test Scenarios
```yaml
test_scenarios:
  - name: "High Price Response"
    description: "Test agent response to high electricity prices"
    input:
      electricity_price: 2.5
      consumption: 4000
    expected_actions:
      - "send_high_cost_alert"
      - "activate_usage_optimization"
      - "notify_user_of_recommendations"
      
  - name: "Usage Spike Response"
    description: "Test agent response to sudden usage increase"
    input:
      consumption_change: 3000
      time: "19:00"
    expected_actions:
      - "send_usage_spike_alert"
      - "identify_high_usage_devices"
      - "suggest_optimization_strategies"
      
  - name: "Solar Optimization"
    description: "Test agent response to solar production start"
    input:
      solar_production: 2000
      battery_level: 60
    expected_actions:
      - "activate_solar_optimization"
      - "charge_battery_if_needed"
      - "schedule_high_usage_devices"
```

## Configuration Examples

### Minimal Configuration
```yaml
# Basic energy monitoring
agent:
  name: "Simple Energy Monitor"
  type: "monitoring"
  enabled: true
  
  data_sources:
    - sensor.electricity_price
    - sensor.house_consumption
  
  triggers:
    - condition: "price > 2.0"
      action: "notify_high_cost"
    
    - condition: "consumption > 5000"
      action: "notify_high_usage"
```

### Advanced Configuration
```yaml
# Full-featured energy monitoring
agent:
  name: "Advanced Energy Monitor"
  type: "monitoring"
  enabled: true
  
  data_sources:
    - sensor.electricity_price
    - sensor.house_consumption
    - sensor.solar_production
    - sensor.battery_level
    - sensor.ev_charger_1
    - sensor.ev_charger_2
  
  monitoring_rules:
    - include: "price_rules"
    - include: "usage_rules"
  
  triggers:
    - include: "time_triggers"
    - include: "event_triggers"
  
  actions:
    - include: "notifications"
    - include: "service_actions"
  
  optimization:
    - include: "load_shifting"
    - include: "usage_reduction"
  
  analysis:
    - include: "calculations"
    - include: "historical_analysis"
  
  metrics:
    - include: "kpis"
    - include: "dashboard"
```

## Getting Started

1. **Choose your configuration level** (minimal, standard, or advanced)
2. **Customize data sources** to match your Home Assistant setup
3. **Adjust thresholds** based on your energy goals and constraints
4. **Test with sample data** to verify agent behavior
5. **Deploy and monitor** agent performance
6. **Iterate and improve** based on real-world usage

## Support

- **Documentation**: Check the main background agent configuration
- **Examples**: Review other agent examples in this directory
- **Testing**: Use the provided test scenarios for validation
- **Community**: Join Home Assistant community forums for help
