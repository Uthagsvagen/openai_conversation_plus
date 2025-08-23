# Prompt Templates for OpenAI Conversation Plus

## Overview
This directory contains prompt templates for different use cases in the OpenAI Conversation Plus integration. These templates provide structured guidance for configuring AI assistants to handle various smart home scenarios.

## Available Templates

### 1. **smart_home_assistant.md**
The main comprehensive template for general smart home assistance.
- **Use case**: Primary assistant configuration
- **Features**: General home monitoring, device control, and assistance
- **Best for**: Getting started with the integration

### 2. **energy_monitoring.md**
Specialized template for energy management and monitoring.
- **Use case**: Energy efficiency and cost optimization
- **Features**: Real-time consumption tracking, EV charging optimization
- **Best for**: Homes with solar panels, EVs, and energy monitoring

### 3. **device_control.md**
Template focused on device automation and control.
- **Use case**: Comprehensive device management
- **Features**: Lighting, climate, entertainment, and appliance control
- **Best for**: Homes with extensive smart device networks

### 4. **family_coordination.md**
Template for family communication and coordination.
- **Use case**: Multi-person household management
- **Features**: Intercom, SMS, calendar coordination, task management
- **Best for**: Families with children, shared schedules, and coordination needs

### 5. **entertainment_media.md**
Template for media and entertainment system management.
- **Use case**: Audio/video system control and multi-room entertainment
- **Features**: Music streaming, TV control, gaming systems, multi-room audio
- **Best for**: Homes with entertainment systems and multi-room audio

## How to Use These Templates

### 1. **Choose Your Base Template**
Start with the template that best matches your primary use case, or combine elements from multiple templates.

### 2. **Customize for Your Home**
- Replace placeholder entity IDs with your actual Home Assistant entities
- Adjust sensor names to match your configuration
- Modify room names and family member information
- Update device types and capabilities

### 3. **Integrate with Your Functions**
Ensure the prompt templates reference the functions you've configured:
- `execute_services` for device control
- `play_track_on_media_player` for music
- `send_sms_by_name` for messaging
- `play_tts_message` for voice responses
- `get_events` for calendar management
- List management functions for tasks

### 4. **Test and Refine**
- Start with basic functionality
- Gradually add complexity
- Test with family members
- Refine based on usage patterns

## Template Structure

Each template follows a consistent structure:
- **Overview**: Purpose and scope
- **Core Features**: Main capabilities
- **Configuration**: Template variables and settings
- **Usage Examples**: Sample commands and interactions
- **Integration Points**: How it works with other systems
- **Best Practices**: Recommendations for optimal use

## Customization Guidelines

### **Anonymization**
- Replace personal names with generic placeholders
- Use fictional addresses and locations
- Remove specific device model numbers
- Generalize family structures and routines

### **Localization**
- Translate to your preferred language
- Adjust cultural references and customs
- Modify time formats and units as needed
- Adapt to local energy pricing structures

### **Integration**
- Ensure entity IDs match your Home Assistant setup
- Verify function availability and configuration
- Test sensor data and automation triggers
- Validate calendar and contact integrations

## Best Practices

### **Security**
- Never include API keys or passwords in prompts
- Use environment variables for sensitive data
- Implement proper access controls
- Regular security reviews and updates

### **Performance**
- Keep prompts concise and focused
- Avoid unnecessary complexity
- Test response times and accuracy
- Monitor resource usage

### **Maintenance**
- Regular prompt updates and improvements
- Version control for prompt changes
- Backup configurations before major changes
- Document customizations and modifications

## Support and Community

For help with these templates:
- Check the main project documentation
- Review the function examples in the `examples/functions/` directory
- Join the Home Assistant community forums
- Contribute improvements and new templates

## License and Attribution

These templates are provided as examples and can be freely modified for personal use. When sharing modifications, please maintain appropriate attribution to the original project.
