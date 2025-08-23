# Security Monitoring Agent Example

## Overview
This agent continuously monitors security events, motion detection, door/window sensors, and other security-related activities to provide automated responses and alerts.

## Agent Configuration

```yaml
agent:
  name: "Security Monitor Agent"
  type: "monitoring"
  enabled: true
  schedule: "continuous"
  priority: "critical"
  
  description: |
    Monitors security events and provides automated responses.
    Detects unusual activity and responds accordingly.
    Manages security system states and notifications.
```

## Data Sources

### Security Sensors
```yaml
data_sources:
  motion_detectors:
    - entity: "binary_sensor.living_room_motion"
      description: "Living room motion detector"
      area: "living_room"
      
    - entity: "binary_sensor.kitchen_motion"
      description: "Kitchen motion detector"
      area: "kitchen"
      
    - entity: "binary_sensor.bedroom_motion"
      description: "Bedroom motion detector"
      area: "bedroom"
      
    - entity: "binary_sensor.garage_motion"
      description: "Garage motion detector"
      area: "garage"
  
  door_sensors:
    - entity: "binary_sensor.front_door"
      description: "Front door sensor"
      area: "entrance"
      
    - entity: "binary_sensor.back_door"
      description: "Back door sensor"
      area: "backyard"
      
    - entity: "binary_sensor.garage_door"
      description: "Garage door sensor"
      area: "garage"
      
    - entity: "binary_sensor.patio_door"
      description: "Patio door sensor"
      area: "patio"
  
  window_sensors:
    - entity: "binary_sensor.living_room_window"
      description: "Living room window sensor"
      area: "living_room"
      
    - entity: "binary_sensor.bedroom_window"
      description: "Bedroom window sensor"
      area: "bedroom"
      
    - entity: "binary_sensor.kitchen_window"
      description: "Kitchen window sensor"
      area: "kitchen"
  
  security_system:
    - entity: "alarm_control_panel.security_system"
      description: "Main security system"
      states: ["disarmed", "armed_home", "armed_away", "triggered"]
      
    - entity: "binary_sensor.security_system_ready"
      description: "Security system ready status"
      
    - entity: "binary_sensor.security_system_trouble"
      description: "Security system trouble indicator"
  
  cameras:
    - entity: "camera.front_door_camera"
      description: "Front door camera"
      area: "entrance"
      
    - entity: "camera.backyard_camera"
      description: "Backyard camera"
      area: "backyard"
      
    - entity: "camera.garage_camera"
      description: "Garage camera"
      area: "garage"
```

## Security Rules

### Motion Detection Rules
```yaml
motion_rules:
  - name: "Normal Daytime Motion"
    condition: "motion_detected"
    time_restriction: "06:00-22:00"
    occupancy: "home"
    action: "log_event"
    priority: "low"
    
  - name: "Evening Motion"
    condition: "motion_detected"
    time_restriction: "22:00-06:00"
    occupancy: "home"
    action: "investigate_motion"
    priority: "medium"
    
  - name: "Motion When Away"
    condition: "motion_detected"
    occupancy: "away"
    action: "security_alert"
    priority: "high"
    
  - name: "Multiple Motion Events"
    condition: "multiple_motion_events"
    threshold: 3
    time_window: 300  # 5 minutes
    action: "security_investigation"
    priority: "high"
```

### Door/Window Rules
```yaml
door_window_rules:
  - name: "Normal Door Usage"
    condition: "door_opened"
    time_restriction: "06:00-22:00"
    occupancy: "home"
    action: "log_event"
    priority: "low"
    
  - name: "Late Night Door Activity"
    condition: "door_opened"
    time_restriction: "22:00-06:00"
    occupancy: "home"
    action: "investigate_door_activity"
    priority: "medium"
    
  - name: "Door Activity When Away"
    condition: "door_opened"
    occupancy: "away"
    action: "immediate_security_alert"
    priority: "critical"
    
  - name: "Window Opened"
    condition: "window_opened"
    occupancy: "any"
    action: "window_security_check"
    priority: "medium"
    
  - name: "Garage Door Activity"
    condition: "garage_door_opened"
    occupancy: "any"
    action: "garage_security_check"
    priority: "medium"
```

### System Status Rules
```yaml
system_rules:
  - name: "System Disarmed"
    condition: "security_system_disarmed"
    action: "log_disarm_event"
    priority: "low"
    
  - name: "System Armed Home"
    condition: "security_system_armed_home"
    action: "activate_home_security"
    priority: "medium"
    
  - name: "System Armed Away"
    condition: "security_system_armed_away"
    action: "activate_away_security"
    priority: "high"
    
  - name: "System Triggered"
    condition: "security_system_triggered"
    action: "emergency_response"
    priority: "critical"
    
  - name: "System Trouble"
    condition: "security_system_trouble"
    action: "system_maintenance_alert"
    priority: "high"
```

## Trigger Conditions

### Time-Based Triggers
```yaml
time_triggers:
  - name: "Sunset Security"
    time: "sunset - 30 minutes"
    action: "activate_evening_security"
    
  - name: "Sunrise Security"
    time: "sunrise + 30 minutes"
    action: "deactivate_night_security"
    
  - name: "Night Mode"
    time: "22:00"
    action: "activate_night_security"
    
  - name: "Morning Mode"
    time: "06:00"
    action: "deactivate_night_security"
    
  - name: "Weekly Security Check"
    time: "monday 09:00"
    action: "weekly_security_audit"
```

### Event-Based Triggers
```yaml
event_triggers:
  - name: "Motion Detection"
    condition: "motion_sensor_activated"
    action: "process_motion_event"
    
  - name: "Door Activity"
    condition: "door_sensor_activated"
    action: "process_door_event"
    
  - name: "Window Activity"
    condition: "window_sensor_activated"
    action: "process_window_event"
    
  - name: "System State Change"
    condition: "security_system_state_changed"
    action: "process_system_state_change"
    
  - name: "Camera Motion"
    condition: "camera_motion_detected"
    action: "process_camera_event"
```

## Automated Actions

### Notifications
```yaml
notifications:
  - name: "Motion Alert"
    trigger: "motion_detected"
    service: "notify.mobile_app"
    data:
      title: "🚨 Motion Detected"
      message: |
        Motion detected in {{ area_name }}
        Time: {{ now().strftime('%H:%M') }}
        Camera: {{ camera_entity }}
      priority: "high"
      
  - name: "Door Activity Alert"
    trigger: "door_activity"
    service: "notify.mobile_app"
    data:
      title: "🚪 Door Activity"
      message: |
        {{ door_name }} was {{ action }}
        Time: {{ now().strftime('%H:%M') }}
        Location: {{ area_name }}
      priority: "medium"
      
  - name: "Security System Alert"
    trigger: "security_system_triggered"
    service: "notify.mobile_app"
    data:
      title: "🚨 SECURITY ALERT"
      message: |
        Security system has been triggered!
        Location: {{ trigger_location }}
        Time: {{ now().strftime('%H:%M') }}
        Immediate response required.
      priority: "critical"
      
  - name: "System Status Update"
    trigger: "system_state_change"
    service: "notify.mobile_app"
    data:
      title: "🔒 Security System"
      message: |
        Security system is now {{ new_state }}
        Previous state: {{ old_state }}
        Time: {{ now().strftime('%H:%M') }}
      priority: "low"
```

### Service Calls
```yaml
service_actions:
  - name: "Activate Home Security"
    trigger: "armed_home"
    service: "script.activate_home_security"
    data:
      motion_sensitivity: "medium"
      camera_recording: "motion_only"
      lighting: "security_mode"
      
  - name: "Activate Away Security"
    trigger: "armed_away"
    service: "script.activate_away_security"
    data:
      motion_sensitivity: "high"
      camera_recording: "continuous"
      lighting: "full_security"
      notify_on_motion: true
      
  - name: "Emergency Response"
    trigger: "system_triggered"
    service: "script.emergency_security_response"
    data:
      activate_sirens: true
      flash_lights: true
      record_all_cameras: true
      notify_authorities: true
      
  - name: "Investigate Motion"
    trigger: "motion_investigation"
    service: "script.investigate_motion"
    data:
      turn_on_lights: true
      record_camera: true
      check_other_sensors: true
      notify_user: true
```

### Camera Actions
```yaml
camera_actions:
  - name: "Record Motion Event"
    trigger: "motion_detected"
    service: "camera.record"
    data:
      entity_id: "{{ motion_camera }}"
      duration: 30
      filename: "motion_{{ now().strftime('%Y%m%d_%H%M%S') }}.mp4"
      
  - name: "Take Snapshot"
    trigger: "security_event"
    service: "camera.snapshot"
    data:
      entity_id: "{{ event_camera }}"
      filename: "security_{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
      
  - name: "Start Recording"
    trigger: "security_alert"
    service: "camera.record"
    data:
      entity_id: "{{ all_cameras }}"
      duration: 300  # 5 minutes
      filename: "security_recording_{{ now().strftime('%Y%m%d_%H%M%S') }}.mp4"
```

## Security Modes

### Home Mode
```yaml
security_modes:
  home:
    name: "Home Security Mode"
    description: "Active when residents are home"
    
    settings:
      motion_sensitivity: "medium"
      camera_recording: "motion_only"
      lighting: "security_mode"
      notifications: "important_only"
      
    rules:
      - "log_normal_activity"
      - "investigate_unusual_activity"
      - "maintain_comfort_lighting"
      - "monitor_external_areas"
```

### Away Mode
```yaml
  away:
    name: "Away Security Mode"
    description: "Active when no residents are home"
    
    settings:
      motion_sensitivity: "high"
      camera_recording: "continuous"
      lighting: "full_security"
      notifications: "all_events"
      
    rules:
      - "immediate_alert_on_any_activity"
      - "continuous_camera_recording"
      - "full_lighting_activation"
      - "authority_notification_on_breach"
```

### Night Mode
```yaml
  night:
    name: "Night Security Mode"
    description: "Active during sleeping hours"
    
    settings:
      motion_sensitivity: "high"
      camera_recording: "motion_only"
      lighting: "minimal"
      notifications: "critical_only"
      
    rules:
      - "investigate_all_motion"
      - "maintain_sleep_environment"
      - "alert_on_external_activity"
      - "log_all_events"
```

## Response Strategies

### Immediate Response
```yaml
immediate_response:
  - name: "Motion Investigation"
    trigger: "motion_detected"
    actions:
      - "turn_on_area_lights"
      - "record_camera_footage"
      - "check_other_sensors"
      - "notify_user"
      
  - name: "Door Breach Response"
    trigger: "unauthorized_door_access"
    actions:
      - "activate_sirens"
      - "flash_all_lights"
      - "record_all_cameras"
      - "notify_authorities"
      - "send_emergency_alert"
```

### Escalation Response
```yaml
escalation_response:
  - name: "Level 1: Investigation"
    trigger: "suspicious_activity"
    actions:
      - "log_event"
      - "notify_user"
      - "increase_monitoring"
      
  - name: "Level 2: Alert"
    trigger: "confirmed_breach"
    actions:
      - "activate_security_system"
      - "notify_all_users"
      - "record_evidence"
      
  - name: "Level 3: Emergency"
    trigger: "security_breach"
    actions:
      - "activate_emergency_protocols"
      - "notify_authorities"
      - "secure_premises"
      - "evacuate_if_necessary"
```

## Monitoring and Logging

### Event Logging
```yaml
event_logging:
  - name: "Security Events"
    events: ["motion", "door_activity", "window_activity", "system_changes"]
    log_level: "info"
    retention: "90 days"
    
  - name: "Alerts and Notifications"
    events: ["security_alerts", "system_notifications", "user_actions"]
    log_level: "warning"
    retention: "1 year"
    
  - name: "Emergency Events"
    events: ["system_triggered", "authority_notifications", "evacuations"]
    log_level: "critical"
    retention: "permanent"
```

### Performance Metrics
```yaml
performance_metrics:
  - name: "Response Time"
    metric: "alert_response_time"
    target: "< 30 seconds"
    calculation: "time_from_trigger_to_action"
    
  - name: "False Positive Rate"
    metric: "false_alarm_rate"
    target: "< 5%"
    calculation: "false_alarms / total_alarms"
    
  - name: "System Uptime"
    metric: "security_system_uptime"
    target: "> 99.9%"
    calculation: "uptime / total_time"
    
  - name: "Event Detection Rate"
    metric: "event_detection_rate"
    target: "> 95%"
    calculation: "detected_events / total_events"
```

## Testing and Validation

### Test Scenarios
```yaml
test_scenarios:
  - name: "Motion Detection Test"
    description: "Test motion sensor response and notification"
    input:
      motion_sensor: "binary_sensor.living_room_motion"
      time: "14:00"
      occupancy: "home"
    expected_actions:
      - "log_motion_event"
      - "turn_on_area_lights"
      - "record_camera_footage"
      - "notify_user"
      
  - name: "Door Breach Test"
    description: "Test unauthorized door access response"
    input:
      door_sensor: "binary_sensor.front_door"
      time: "23:00"
      occupancy: "away"
      security_system: "armed_away"
    expected_actions:
      - "trigger_security_alarm"
      - "activate_sirens"
      - "flash_all_lights"
      - "record_all_cameras"
      - "notify_authorities"
      - "send_emergency_alert"
      
  - name: "System State Change Test"
    description: "Test security system state change handling"
    input:
      old_state: "disarmed"
      new_state: "armed_away"
      user: "authorized_user"
    expected_actions:
      - "log_state_change"
      - "activate_away_security"
      - "notify_users"
      - "update_system_status"
```

## Configuration Examples

### Minimal Configuration
```yaml
# Basic security monitoring
agent:
  name: "Simple Security Monitor"
  type: "monitoring"
  enabled: true
  
  data_sources:
    - binary_sensor.motion_detector
    - binary_sensor.door_sensor
    - alarm_control_panel.security_system
  
  triggers:
    - condition: "motion_detected"
      action: "notify_motion"
    
    - condition: "door_opened"
      action: "notify_door_activity"
    
    - condition: "system_armed"
      action: "activate_security"
```

### Advanced Configuration
```yaml
# Full-featured security monitoring
agent:
  name: "Advanced Security Monitor"
  type: "monitoring"
  enabled: true
  
  data_sources:
    - include: "security_sensors"
    - include: "cameras"
    - include: "security_system"
  
  security_rules:
    - include: "motion_rules"
    - include: "door_window_rules"
    - include: "system_rules"
  
  triggers:
    - include: "time_triggers"
    - include: "event_triggers"
  
  actions:
    - include: "notifications"
    - include: "service_actions"
    - include: "camera_actions"
  
  security_modes:
    - include: "home_mode"
    - include: "away_mode"
    - include: "night_mode"
  
  response_strategies:
    - include: "immediate_response"
    - include: "escalation_response"
  
  monitoring:
    - include: "event_logging"
    - include: "performance_metrics"
```

## Getting Started

1. **Choose your configuration level** (minimal, standard, or advanced)
2. **Customize data sources** to match your security setup
3. **Adjust security rules** based on your security requirements
4. **Test with sample scenarios** to verify agent behavior
5. **Deploy and monitor** agent performance
6. **Iterate and improve** based on real-world usage

## Support

- **Documentation**: Check the main background agent configuration
- **Examples**: Review other agent examples in this directory
- **Testing**: Use the provided test scenarios for validation
- **Community**: Join Home Assistant community forums for help
