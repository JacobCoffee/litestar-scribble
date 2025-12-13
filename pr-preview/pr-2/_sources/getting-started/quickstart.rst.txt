Quickstart
==========

This guide walks you through using scribbl-py for the first time.


Running the Application
-----------------------

Start the application:

.. code-block:: bash

   make serve

Open http://127.0.0.1:8000 in your browser.


Using the Canvas Editor
-----------------------

1. Navigate to http://127.0.0.1:8000/ui/
2. Click "New Canvas" to create a drawing
3. Use the toolbar to select tools:

   - **Pen** - Freehand drawing
   - **Line** - Straight lines
   - **Rectangle** - Rectangles and squares
   - **Ellipse** - Circles and ellipses
   - **Text** - Add text labels
   - **Eraser** - Erase elements
   - **Fill** - Fill shapes with color

4. Choose colors and brush sizes
5. Use Ctrl+Z / Ctrl+Y for undo/redo
6. Export your drawing as PNG, SVG, or JSON


Playing Canvas Clash
--------------------

Canvas Clash is a Pictionary-style multiplayer game.

Starting a Game
~~~~~~~~~~~~~~~

1. Navigate to http://127.0.0.1:8000/canvas-clash/
2. Click "Create Room" or enter a room code to join
3. Share the room code with friends
4. Wait for players to join (minimum 2)
5. The host clicks "Start Game"

Gameplay
~~~~~~~~

1. Each round, one player becomes the drawer
2. The drawer selects a word from three options
3. Draw the word while others guess in chat
4. Points are awarded for:

   - **Guessing correctly** (faster = more points)
   - **Drawing** (based on how many players guess)

5. The player with the most points wins!

Multiplayer Testing
~~~~~~~~~~~~~~~~~~~

To test multiplayer locally:

.. code-block:: bash

   # Open two browser windows
   make game-test

This opens one regular and one incognito window for testing with separate sessions.


Using the REST API
------------------

scribbl-py provides a REST API for programmatic access.

Creating a Canvas
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST http://127.0.0.1:8000/api/canvases \
     -H "Content-Type: application/json" \
     -d '{"name": "My Canvas", "width": 800, "height": 600}'

Response:

.. code-block:: json

   {
     "id": "550e8400-e29b-41d4-a716-446655440000",
     "name": "My Canvas",
     "width": 800,
     "height": 600,
     "created_at": "2024-01-01T00:00:00Z",
     "elements": []
   }

Adding a Stroke
~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST http://127.0.0.1:8000/api/canvases/{id}/elements/strokes \
     -H "Content-Type: application/json" \
     -d '{
       "points": [{"x": 10, "y": 10}, {"x": 100, "y": 100}],
       "style": {"stroke_color": "#000000", "stroke_width": 2}
     }'

Exporting
~~~~~~~~~

.. code-block:: bash

   # Export as JSON
   curl http://127.0.0.1:8000/api/canvases/{id}/export/json

   # Export as SVG
   curl http://127.0.0.1:8000/api/canvases/{id}/export/svg

   # Export as PNG
   curl http://127.0.0.1:8000/api/canvases/{id}/export/png -o canvas.png


WebSocket Real-time Collaboration
---------------------------------

Connect to a canvas for real-time updates:

.. code-block:: javascript

   const ws = new WebSocket('ws://127.0.0.1:8000/ws/canvas/{canvas_id}');

   // Join the canvas session
   ws.onopen = () => {
     ws.send(JSON.stringify({
       type: 'join',
       user_id: 'user123',
       user_name: 'Alice'
     }));
   };

   // Handle messages
   ws.onmessage = (event) => {
     const message = JSON.parse(event.data);
     console.log('Received:', message);
   };

   // Add an element
   ws.send(JSON.stringify({
     type: 'element_add',
     element: {
       type: 'stroke',
       points: [{x: 10, y: 10}, {x: 100, y: 100}],
       style: {stroke_color: '#000000', stroke_width: 2}
     }
   }));


Using the Plugin in Your Own App
--------------------------------

Integrate scribbl-py into your Litestar application:

.. code-block:: python

   from litestar import Litestar
   from scribbl_py import ScribblPlugin, ScribblConfig

   app = Litestar(
       plugins=[ScribblPlugin(ScribblConfig())],
   )

With custom configuration:

.. code-block:: python

   from scribbl_py import (
       ScribblPlugin,
       ScribblConfig,
       InMemoryStorage,
   )

   config = ScribblConfig(
       storage=InMemoryStorage(),
       api_path="/api/v1",
       enable_websocket=True,
       enable_game=True,
   )

   app = Litestar(
       plugins=[ScribblPlugin(config)],
   )


Next Steps
----------

- :doc:`/guides/configuration` - Configure OAuth, telemetry, and more
- :doc:`/guides/development` - Set up a development environment
- :doc:`/guides/deployment` - Deploy to production
- :doc:`/api/index` - Complete API reference
