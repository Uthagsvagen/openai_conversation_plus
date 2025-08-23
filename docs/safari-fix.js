// Safari fix for uninitialized variable in ha-assist-chat
// Place this file in your Home Assistant www/ directory

if (navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')) {
  console.log('Applying Safari fix for ha-assist-chat');
  
  // Patch to prevent uninitialized variable access
  const originalAddEventListener = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function(type, listener, options) {
    if (type === 'message' && this.constructor.name === 'WebSocket') {
      const wrappedListener = function(event) {
        try {
          listener.call(this, event);
        } catch (e) {
          if (e.message && e.message.includes('Cannot access uninitialized variable')) {
            console.warn('Caught Safari uninitialized variable error, ignoring:', e);
            return;
          }
          throw e;
        }
      };
      return originalAddEventListener.call(this, type, wrappedListener, options);
    }
    return originalAddEventListener.call(this, type, listener, options);
  };
}
