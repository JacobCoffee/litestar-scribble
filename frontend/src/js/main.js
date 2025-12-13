/**
 * Scribbl Frontend JavaScript
 *
 * Handles canvas interactions, WebSocket connections, and HTMX enhancements.
 */

// Theme management
const ThemeManager = {
  STORAGE_KEY: 'scribbl-theme',

  init() {
    const savedTheme = localStorage.getItem(this.STORAGE_KEY) || 'light';
    this.setTheme(savedTheme);

    // Listen for theme toggle events
    document.addEventListener('theme-toggle', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      this.setTheme(next);
    });
  },

  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(this.STORAGE_KEY, theme);
  },

  getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }
};

// WebSocket connection manager
const WebSocketManager = {
  socket: null,
  canvasId: null,
  userId: null,
  userName: null,
  connectionState: 'disconnected',
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
  reconnectTimeoutId: null,
  messageQueue: [],
  isReconnecting: false,

  init(canvasId, userId, userName) {
    this.canvasId = canvasId;
    this.userId = userId;
    this.userName = userName;
    this.connect();
  },

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/canvas/${this.canvasId}`;

    this.setConnectionState('connecting');

    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        this.handleConnectionOpen();
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.socket.onclose = (event) => {
        this.handleConnectionClose(event);
      };

      this.socket.onerror = (error) => {
        this.handleConnectionError(error);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.setConnectionState('disconnected');
      this.showToast('Failed to establish connection', 'error');
      this.attemptReconnect();
    }
  },

  handleConnectionOpen() {
    console.log('WebSocket connected');
    const wasReconnecting = this.isReconnecting;
    this.reconnectAttempts = 0;
    this.isReconnecting = false;
    this.setConnectionState('connected');

    // Send join message
    this.send({
      type: 'join',
      user_id: this.userId,
      user_name: this.userName
    });

    // Show success message if reconnecting
    if (wasReconnecting) {
      this.showToast('Reconnected successfully', 'success');
    }

    // Flush queued messages
    this.flushMessageQueue();
  },

  handleConnectionClose(event) {
    console.log('WebSocket closed', event.code, event.reason);

    // Only attempt reconnect if not a normal closure (code 1000)
    // and not already reconnecting
    if (event.code !== 1000 && !this.isReconnecting) {
      this.setConnectionState('disconnected');
      this.showToast('Connection lost', 'warning');
      this.attemptReconnect();
    } else {
      this.setConnectionState('disconnected');
    }
  },

  handleConnectionError(error) {
    console.error('WebSocket error:', error);

    // Only update state and show message if not already in an error state
    if (this.connectionState !== 'disconnected' && this.connectionState !== 'reconnecting') {
      this.setConnectionState('disconnected');
      this.showToast('Connection error occurred', 'error');
    }
  },

  attemptReconnect() {
    // Prevent multiple reconnect attempts
    if (this.isReconnecting) {
      return;
    }

    // Clear any existing reconnect timeout
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.isReconnecting = true;

      // Exponential backoff: 1s, 2s, 4s, 8s, 16s
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      this.setConnectionState('reconnecting');
      this.showToast(
        `Reconnecting in ${delay / 1000}s... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
        'info'
      );

      this.reconnectTimeoutId = setTimeout(() => {
        console.log(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, delay);
    } else {
      // Max reconnect attempts reached
      this.isReconnecting = false;
      this.setConnectionState('disconnected');
      this.showToast(
        'Connection lost. Maximum reconnection attempts reached. Please refresh the page.',
        'error'
      );
    }
  },

  setConnectionState(state) {
    this.connectionState = state;
    this.updateStatus(state);
  },

  updateStatus(status) {
    const indicator = document.querySelector('.connection-status-dot');
    if (indicator) {
      indicator.className = `connection-status-dot connection-status-dot-${status}`;
    }

    const label = document.querySelector('.connection-status-label');
    if (label) {
      const labels = {
        connected: 'Connected',
        disconnected: 'Disconnected',
        connecting: 'Connecting...',
        reconnecting: 'Reconnecting...'
      };
      label.textContent = labels[status] || status;
    }
  },

  send(message) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      // Queue message if not connected
      console.log('Queueing message (not connected):', message.type);
      this.queueMessage(message);
    }
  },

  queueMessage(message) {
    // Don't queue certain message types
    const skipQueueTypes = ['cursor_move', 'join'];
    if (skipQueueTypes.includes(message.type)) {
      return;
    }

    this.messageQueue.push(message);

    // Limit queue size to prevent memory issues
    const maxQueueSize = 50;
    if (this.messageQueue.length > maxQueueSize) {
      this.messageQueue.shift();
      console.warn('Message queue full, dropping oldest message');
    }
  },

  flushMessageQueue() {
    if (this.messageQueue.length === 0) {
      return;
    }

    console.log(`Flushing ${this.messageQueue.length} queued messages`);

    const messages = [...this.messageQueue];
    this.messageQueue = [];

    messages.forEach(message => {
      this.send(message);
    });
  },

  disconnect() {
    // Clean disconnect
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    this.isReconnecting = false;

    if (this.socket) {
      this.socket.close(1000, 'Client initiated disconnect');
      this.socket = null;
    }

    this.setConnectionState('disconnected');
  },

  handleMessage(message) {
    const handlers = {
      'sync': this.handleSync.bind(this),
      'user_joined': this.handleUserJoined.bind(this),
      'user_left': this.handleUserLeft.bind(this),
      'element_added': this.handleElementAdded.bind(this),
      'element_updated': this.handleElementUpdated.bind(this),
      'element_deleted': this.handleElementDeleted.bind(this),
      'cursor_moved': this.handleCursorMoved.bind(this),
      'undo_result': this.handleUndoResult.bind(this),
      'redo_result': this.handleRedoResult.bind(this),
      'error': this.handleError.bind(this),
      'stroke_started': this.handleStrokeStarted.bind(this),
      'stroke_continued': this.handleStrokeContinued.bind(this),
      'stroke_ended': this.handleStrokeEnded.bind(this)
    };

    const handler = handlers[message.type];
    if (handler) {
      handler(message);
    }
  },

  handleSync(message) {
    // Dispatch custom event for canvas to handle
    document.dispatchEvent(new CustomEvent('canvas-sync', { detail: message }));
  },

  handleUserJoined(message) {
    this.showToast(`${message.user_name} joined`, 'info');
    document.dispatchEvent(new CustomEvent('user-joined', { detail: message }));
  },

  handleUserLeft(message) {
    this.showToast(`${message.user_name} left`, 'info');
    document.dispatchEvent(new CustomEvent('user-left', { detail: message }));
  },

  handleElementAdded(message) {
    document.dispatchEvent(new CustomEvent('element-added', { detail: message }));
  },

  handleElementUpdated(message) {
    document.dispatchEvent(new CustomEvent('element-updated', { detail: message }));
  },

  handleElementDeleted(message) {
    document.dispatchEvent(new CustomEvent('element-deleted', { detail: message }));
  },

  handleCursorMoved(message) {
    document.dispatchEvent(new CustomEvent('cursor-moved', { detail: message }));
  },

  handleUndoResult(message) {
    // Trigger canvas refresh by dispatching sync event
    document.dispatchEvent(new CustomEvent('canvas-sync', { detail: message }));
  },

  handleRedoResult(message) {
    // Trigger canvas refresh by dispatching sync event
    document.dispatchEvent(new CustomEvent('canvas-sync', { detail: message }));
  },

  handleError(message) {
    console.error('Server error:', message.message);
    this.showToast(message.message, 'error');
  },

  handleStrokeStarted(message) {
    document.dispatchEvent(new CustomEvent('stroke-started', { detail: message }));
  },

  handleStrokeContinued(message) {
    document.dispatchEvent(new CustomEvent('stroke-continued', { detail: message }));
  },

  handleStrokeEnded(message) {
    document.dispatchEvent(new CustomEvent('stroke-ended', { detail: message }));
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const alertClass = {
      'info': 'alert-info',
      'success': 'alert-success',
      'warning': 'alert-warning',
      'error': 'alert-error'
    }[type] || 'alert-info';

    const toast = document.createElement('div');
    toast.className = `alert ${alertClass} animate-fade-in`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3000);
  },

  // Canvas operations
  addElement(elementType, elementData) {
    this.send({
      type: 'element_add',
      element_type: elementType,
      element_data: elementData
    });
  },

  updateElement(elementId, updates) {
    this.send({
      type: 'element_update',
      element_id: elementId,
      element_data: updates
    });
  },

  deleteElement(elementId) {
    this.send({ type: 'element_delete', element_id: elementId });
  },

  moveCursor(x, y) {
    this.send({ type: 'cursor_move', x, y });
  },

  undo() {
    this.send({ type: 'undo' });
  },

  redo() {
    this.send({ type: 'redo' });
  },

  // Stroke streaming methods
  startStroke(strokeId, point, style) {
    this.send({
      type: 'stroke_start',
      stroke_id: strokeId,
      point: point,
      style: style
    });
  },

  continueStroke(strokeId, points) {
    this.send({
      type: 'stroke_continue',
      stroke_id: strokeId,
      points: points
    });
  },

  endStroke(strokeId) {
    this.send({
      type: 'stroke_end',
      stroke_id: strokeId
    });
  }
};

// Canvas drawing manager
const CanvasManager = {
  canvas: null,
  ctx: null,
  tempCanvas: null,
  tempCtx: null,
  elements: [],
  selectedTool: 'pen',
  currentColor: '#000000',
  strokeWidth: 2,
  isDrawing: false,
  currentPath: [],
  startPoint: null,
  endPoint: null,
  currentStrokeId: null,
  lastStreamTime: 0,
  streamThrottle: 50, // milliseconds
  remoteStrokes: new Map(),

  init(canvasElement) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');

    // Create temporary canvas for shape preview
    this.tempCanvas = document.createElement('canvas');
    this.tempCtx = this.tempCanvas.getContext('2d');

    this.setupEventListeners();
    this.resize();
  },

  setupEventListeners() {
    // Mouse events
    this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
    this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
    this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
    this.canvas.addEventListener('mouseleave', this.handleMouseUp.bind(this));

    // Touch events
    this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
    this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
    this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));

    // Resize
    window.addEventListener('resize', this.resize.bind(this));

    // Custom events from WebSocket
    document.addEventListener('canvas-sync', (e) => this.syncCanvas(e.detail));
    document.addEventListener('element-added', (e) => this.addRemoteElement(e.detail));
    document.addEventListener('element-updated', (e) => this.updateRemoteElement(e.detail));
    document.addEventListener('element-deleted', (e) => this.deleteRemoteElement(e.detail));
    document.addEventListener('stroke-started', (e) => this.handleRemoteStrokeStart(e.detail));
    document.addEventListener('stroke-continued', (e) => this.handleRemoteStrokeContinue(e.detail));
    document.addEventListener('stroke-ended', (e) => this.handleRemoteStrokeEnd(e.detail));
  },

  resize() {
    const container = this.canvas.parentElement;
    const rect = container.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;

    // Resize temp canvas to match
    this.tempCanvas.width = rect.width;
    this.tempCanvas.height = rect.height;

    this.redraw();
  },

  handleMouseDown(e) {
    const point = this.getCanvasPoint(e);
    this.startDrawing(point);
  },

  handleMouseMove(e) {
    const point = this.getCanvasPoint(e);

    // Send cursor position via WebSocket
    if (WebSocketManager.socket) {
      WebSocketManager.moveCursor(point.x, point.y);
    }

    if (this.isDrawing) {
      this.continueDrawing(point);
    }
  },

  handleMouseUp() {
    this.endDrawing();
  },

  handleTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const point = this.getCanvasPoint(touch);
    this.startDrawing(point);
  },

  handleTouchMove(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const point = this.getCanvasPoint(touch);
    this.continueDrawing(point);
  },

  handleTouchEnd(e) {
    e.preventDefault();
    this.endDrawing();
  },

  getCanvasPoint(e) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  },

  startDrawing(point) {
    this.isDrawing = true;
    this.startPoint = point;

    // Handle different tools
    if (this.selectedTool === 'text') {
      // For text tool, show prompt immediately
      this.handleTextTool(point);
      this.isDrawing = false;
      return;
    }

    if (this.selectedTool === 'eraser') {
      // For eraser, start erasing immediately
      this.handleEraser(point);
      return;
    }

    if (this.selectedTool === 'rectangle' || this.selectedTool === 'ellipse') {
      // For shapes, just store start point and wait for drag
      this.currentPath = [];
      return;
    }

    // For pen tool, start drawing stroke
    this.currentPath = [point];
    this.currentStrokeId = crypto.randomUUID();
    this.ctx.beginPath();
    this.ctx.moveTo(point.x, point.y);
    this.ctx.strokeStyle = this.currentColor;
    this.ctx.lineWidth = this.strokeWidth;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    // Send stroke start message
    WebSocketManager.startStroke(this.currentStrokeId, point, {
      stroke_color: this.currentColor,
      stroke_width: this.strokeWidth
    });
  },

  continueDrawing(point) {
    if (!this.isDrawing) return;

    // Handle eraser
    if (this.selectedTool === 'eraser') {
      this.handleEraser(point);
      return;
    }

    // Handle shape tools (rectangle, ellipse) - show preview
    if (this.selectedTool === 'rectangle' || this.selectedTool === 'ellipse') {
      this.endPoint = point;
      this.drawShapePreview(point);
      return;
    }

    // Handle pen tool - draw stroke
    this.currentPath.push(point);
    this.ctx.lineTo(point.x, point.y);
    this.ctx.stroke();

    // Throttle stroke continue messages
    const now = Date.now();
    if (now - this.lastStreamTime >= this.streamThrottle && this.currentStrokeId) {
      // Get new points since last stream
      const streamBatchSize = Math.max(1, Math.floor(this.currentPath.length / 10));
      const newPoints = this.currentPath.slice(-streamBatchSize);

      WebSocketManager.continueStroke(this.currentStrokeId, newPoints);
      this.lastStreamTime = now;
    }
  },

  endDrawing() {
    if (!this.isDrawing) return;

    this.isDrawing = false;

    // Clear temp canvas
    this.tempCtx.clearRect(0, 0, this.tempCanvas.width, this.tempCanvas.height);

    // Handle different tools
    if (this.selectedTool === 'rectangle' || this.selectedTool === 'ellipse') {
      // Send shape to server
      if (this.startPoint && this.endPoint) {
        const x = Math.min(this.startPoint.x, this.endPoint.x);
        const y = Math.min(this.startPoint.y, this.endPoint.y);
        const width = Math.abs(this.endPoint.x - this.startPoint.x);
        const height = Math.abs(this.endPoint.y - this.startPoint.y);

        // Only send if shape has meaningful size
        if (width > 2 && height > 2) {
          WebSocketManager.addElement('shape', {
            shape_type: this.selectedTool,
            x: x,
            y: y,
            width: width,
            height: height,
            style: {
              stroke_color: this.currentColor,
              stroke_width: this.strokeWidth
            }
          });
        }
      }
      this.startPoint = null;
      this.endPoint = null;
      this.redraw();
      return;
    }

    if (this.selectedTool === 'eraser') {
      // Eraser handled in handleEraser
      this.startPoint = null;
      return;
    }

    // For pen tool, send stroke end
    if (this.currentPath.length > 1 && this.currentStrokeId) {
      WebSocketManager.endStroke(this.currentStrokeId);
    }

    this.currentPath = [];
    this.currentStrokeId = null;
    this.startPoint = null;
  },

  drawShapePreview(endPoint) {
    if (!this.startPoint) return;

    // Redraw canvas to clear previous preview
    this.redraw();

    // Draw preview shape on main canvas
    const x = Math.min(this.startPoint.x, endPoint.x);
    const y = Math.min(this.startPoint.y, endPoint.y);
    const width = Math.abs(endPoint.x - this.startPoint.x);
    const height = Math.abs(endPoint.y - this.startPoint.y);

    this.ctx.strokeStyle = this.currentColor;
    this.ctx.lineWidth = this.strokeWidth;

    if (this.selectedTool === 'rectangle') {
      this.ctx.strokeRect(x, y, width, height);
    } else if (this.selectedTool === 'ellipse') {
      this.ctx.beginPath();
      this.ctx.ellipse(
        x + width / 2,
        y + height / 2,
        width / 2,
        height / 2,
        0, 0, 2 * Math.PI
      );
      this.ctx.stroke();
    }
  },

  handleTextTool(point) {
    const userText = prompt('Enter text:');
    if (userText && userText.trim()) {
      WebSocketManager.addElement('text', {
        content: userText,
        x: point.x,
        y: point.y,
        font_size: 16,
        font_family: 'sans-serif',
        style: {
          fill_color: this.currentColor
        }
      });
    }
  },

  handleEraser(point) {
    // Find elements near cursor position
    const eraserRadius = this.strokeWidth * 3;
    const elementsToDelete = [];

    for (const element of this.elements) {
      let shouldDelete = false;

      if (element.type === 'stroke') {
        // Check if any point in the stroke is near the cursor
        for (const p of element.points || []) {
          const distance = Math.sqrt(
            Math.pow(p.x - point.x, 2) + Math.pow(p.y - point.y, 2)
          );
          if (distance < eraserRadius) {
            shouldDelete = true;
            break;
          }
        }
      } else if (element.type === 'shape') {
        // Check if cursor is inside shape bounds
        if (point.x >= element.x && point.x <= element.x + element.width &&
            point.y >= element.y && point.y <= element.y + element.height) {
          shouldDelete = true;
        }
      } else if (element.type === 'text') {
        // Simple bounds check for text
        const textWidth = 100;
        const textHeight = element.font_size || 16;
        if (point.x >= element.x && point.x <= element.x + textWidth &&
            point.y >= element.y - textHeight && point.y <= element.y) {
          shouldDelete = true;
        }
      }

      if (shouldDelete && element.id) {
        elementsToDelete.push(element.id);
      }
    }

    // Delete found elements
    for (const elementId of elementsToDelete) {
      WebSocketManager.deleteElement(elementId);
    }
  },

  setTool(tool) {
    console.log('[CanvasManager] setTool:', tool);
    this.selectedTool = tool;
  },

  setColor(color) {
    console.log('[CanvasManager] setColor:', color);
    this.currentColor = color;
  },

  setStrokeWidth(width) {
    console.log('[CanvasManager] setStrokeWidth:', width);
    this.strokeWidth = width;
  },

  syncCanvas(data) {
    // Verify canvas_id matches if provided
    const messageCanvasId = data.canvas_id || data.canvas_data?.id;
    const currentCanvasId = this.canvas?.dataset?.canvasId;

    if (messageCanvasId && currentCanvasId && messageCanvasId !== currentCanvasId) {
      console.warn('[CanvasManager] Ignoring sync for different canvas:', messageCanvasId, 'vs', currentCanvasId);
      return;
    }

    // Server sends elements in canvas_data.elements or directly in elements
    const serverElements = data.canvas_data?.elements || data.elements || [];
    console.log('[CanvasManager] syncCanvas: received', serverElements.length, 'elements');
    this.elements = serverElements.map(e => this.convertServerElement(e));
    this.redraw();
  },

  addRemoteElement(data) {
    // Server sends element_data, convert to internal format
    const element = this.convertServerElement(data.element_data);
    this.elements.push(element);
    this.drawElement(element);
  },

  convertServerElement(serverData) {
    // Convert server format to internal drawing format
    const element = {
      id: serverData.id,
      type: serverData.element_type,
      style: serverData.style
    };

    if (serverData.stroke_data) {
      element.points = serverData.stroke_data.points;
    }
    if (serverData.shape_data) {
      element.shape_type = serverData.shape_data.shape_type;
      element.x = serverData.position?.x || 0;
      element.y = serverData.position?.y || 0;
      element.width = serverData.shape_data.width;
      element.height = serverData.shape_data.height;
    }
    if (serverData.text_data) {
      element.content = serverData.text_data.content;
      element.font_size = serverData.text_data.font_size;
      element.font_family = serverData.text_data.font_family;
      element.x = serverData.position?.x || 0;
      element.y = serverData.position?.y || 0;
    }

    return element;
  },

  updateRemoteElement(data) {
    const index = this.elements.findIndex(e => e.id === data.element_id);
    if (index !== -1) {
      Object.assign(this.elements[index], data);
      this.redraw();
    }
  },

  deleteRemoteElement(data) {
    this.elements = this.elements.filter(e => e.id !== data.element_id);
    this.redraw();
  },

  redraw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.elements.forEach(element => this.drawElement(element));

    // Draw remote strokes in progress
    this.remoteStrokes.forEach(stroke => {
      if (stroke.points && stroke.points.length > 0) {
        this.drawStroke(stroke);
      }
    });
  },

  handleRemoteStrokeStart(data) {
    const { stroke_id, point, style } = data;

    // Create a temporary stroke object
    this.remoteStrokes.set(stroke_id, {
      type: 'stroke',
      points: [point],
      style: style
    });

    // Redraw to show the start point
    this.redraw();
  },

  handleRemoteStrokeContinue(data) {
    const { stroke_id, points } = data;

    // Get existing remote stroke
    const stroke = this.remoteStrokes.get(stroke_id);
    if (stroke) {
      // Add new points
      stroke.points.push(...points);

      // Redraw to show updated stroke
      this.redraw();
    }
  },

  handleRemoteStrokeEnd(data) {
    const { stroke_id, element_data } = data;

    // Remove temporary stroke
    this.remoteStrokes.delete(stroke_id);

    // Add the final element
    if (element_data) {
      const element = this.convertServerElement(element_data);
      this.elements.push(element);
    }

    // Redraw to show final stroke
    this.redraw();
  },

  drawElement(element) {
    switch (element.type) {
      case 'stroke':
        this.drawStroke(element);
        break;
      case 'shape':
        this.drawShape(element);
        break;
      case 'text':
        this.drawText(element);
        break;
    }
  },

  drawStroke(stroke) {
    if (!stroke.points || stroke.points.length < 2) return;

    this.ctx.beginPath();
    this.ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

    for (let i = 1; i < stroke.points.length; i++) {
      this.ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }

    this.ctx.strokeStyle = stroke.style?.stroke_color || '#000000';
    this.ctx.lineWidth = stroke.style?.stroke_width || 2;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    this.ctx.stroke();
  },

  drawShape(shape) {
    const style = shape.style || {};
    this.ctx.fillStyle = style.fill_color || 'transparent';
    this.ctx.strokeStyle = style.stroke_color || '#000000';
    this.ctx.lineWidth = style.stroke_width || 2;

    switch (shape.shape_type) {
      case 'rectangle':
        if (style.fill_color) {
          this.ctx.fillRect(shape.x, shape.y, shape.width, shape.height);
        }
        this.ctx.strokeRect(shape.x, shape.y, shape.width, shape.height);
        break;
      case 'ellipse':
        this.ctx.beginPath();
        this.ctx.ellipse(
          shape.x + shape.width / 2,
          shape.y + shape.height / 2,
          shape.width / 2,
          shape.height / 2,
          0, 0, 2 * Math.PI
        );
        if (style.fill_color) this.ctx.fill();
        this.ctx.stroke();
        break;
    }
  },

  drawText(text) {
    this.ctx.font = `${text.font_size || 16}px ${text.font_family || 'sans-serif'}`;
    this.ctx.fillStyle = text.style?.fill_color || '#000000';
    this.ctx.fillText(text.content, text.x, text.y);
  }
};

// Remote cursor manager
const CursorManager = {
  cursors: new Map(),

  init() {
    document.addEventListener('cursor-moved', (e) => this.updateCursor(e.detail));
    document.addEventListener('user-left', (e) => this.removeCursor(e.detail.user_id));
  },

  updateCursor(data) {
    let cursor = this.cursors.get(data.user_id);

    if (!cursor) {
      cursor = this.createCursor(data.user_id, data.user_name);
      this.cursors.set(data.user_id, cursor);
    }

    cursor.style.transform = `translate(${data.x}px, ${data.y}px)`;
  },

  createCursor(userId, userName) {
    const cursor = document.createElement('div');
    cursor.className = 'user-cursor';
    cursor.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M5.5 3.21V20.8l5.22-5.22h8.07L5.5 3.21z"/>
      </svg>
      <span class="user-cursor-label">${userName || 'User'}</span>
    `;

    const container = document.querySelector('.canvas-container');
    if (container) {
      container.appendChild(cursor);
    }

    return cursor;
  },

  removeCursor(userId) {
    const cursor = this.cursors.get(userId);
    if (cursor) {
      cursor.remove();
      this.cursors.delete(userId);
    }
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Scribbl] DOMContentLoaded - initializing...');

  // Initialize theme
  ThemeManager.init();

  // Initialize cursor manager
  CursorManager.init();

  // Initialize canvas if present
  const canvasElement = document.getElementById('drawing-canvas');
  console.log('[Scribbl] Canvas element:', canvasElement);

  if (canvasElement) {
    console.log('[Scribbl] Initializing CanvasManager...');
    CanvasManager.init(canvasElement);
    console.log('[Scribbl] CanvasManager initialized:', CanvasManager.canvas ? 'success' : 'failed');

    // Get canvas ID from data attribute
    const canvasId = canvasElement.dataset.canvasId;
    const userId = canvasElement.dataset.userId || crypto.randomUUID();
    const userName = canvasElement.dataset.userName || 'Anonymous';

    console.log('[Scribbl] Canvas ID:', canvasId, 'User:', userName);

    if (canvasId) {
      WebSocketManager.init(canvasId, userId, userName);
    }
  } else {
    console.log('[Scribbl] No canvas element found on this page');
  }

  // Tool selection
  document.querySelectorAll('[data-tool]').forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active class from all tool buttons
      document.querySelectorAll('[data-tool]').forEach(b => {
        b.classList.remove('btn-primary', 'toolbar-btn-active');
        b.classList.add('toolbar-btn');
      });
      // Add active class to clicked button
      btn.classList.remove('toolbar-btn');
      btn.classList.add('btn-primary', 'toolbar-btn-active');

      // Update canvas tool if canvas is initialized
      if (CanvasManager.canvas) {
        CanvasManager.setTool(btn.dataset.tool);
        console.log('Tool selected:', btn.dataset.tool);
      }
    });
  });

  // Color picker with preview sync
  const colorPicker = document.getElementById('color-picker');
  const strokePreview = document.getElementById('stroke-preview');

  if (colorPicker) {
    colorPicker.addEventListener('input', (e) => {
      const color = e.target.value;
      CanvasManager.setColor(color);

      // Update stroke preview color
      if (strokePreview) {
        strokePreview.style.backgroundColor = color;
      }
    });
  }

  // Stroke width with live preview
  const strokeWidth = document.getElementById('stroke-width');
  const strokeValue = document.getElementById('stroke-value');

  if (strokeWidth && strokeValue && strokePreview) {
    const updateStrokeDisplay = (value) => {
      const width = parseInt(value, 10);
      strokeValue.textContent = `${width}px`;

      // Update preview circle size (clamped to reasonable visual size)
      const previewSize = Math.min(width * 2, 40);
      strokePreview.style.width = `${previewSize}px`;
      strokePreview.style.height = `${previewSize}px`;

      CanvasManager.setStrokeWidth(width);
    };

    strokeWidth.addEventListener('input', (e) => {
      updateStrokeDisplay(e.target.value);
    });

    // Initialize display
    updateStrokeDisplay(strokeWidth.value);
  }

  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('theme-toggle'));
    });
  }

  // Undo/Redo buttons
  document.getElementById('undo-btn')?.addEventListener('click', () => {
    WebSocketManager.undo();
  });
  document.getElementById('redo-btn')?.addEventListener('click', () => {
    WebSocketManager.redo();
  });
});

// Export for external use
window.Scribbl = {
  ThemeManager,
  WebSocketManager,
  CanvasManager,
  CursorManager
};
