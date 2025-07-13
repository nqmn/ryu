#!/usr/bin/env python3
"""
GUI Controller for Middleware

This module provides static file serving for the modern HTML GUI dashboard
that interfaces with the middleware API.
"""

import os
import logging
from webob.static import DirectoryApp

from ryu.app.wsgi import ControllerBase, route

LOG = logging.getLogger(__name__)


class MiddlewareGUIController(ControllerBase):
    """
    GUI Controller for serving static HTML/CSS/JS files
    
    Serves the modern topology dashboard that interfaces with the v2.0
    middleware API endpoints.
    """
    
    def __init__(self, req, link, data, **config):
        super(MiddlewareGUIController, self).__init__(req, link, data, **config)
        
        # Get the path to the GUI files
        middleware_path = os.path.dirname(__file__)
        gui_path = os.path.join(middleware_path, 'gui')
        
        # Create GUI directory if it doesn't exist
        if not os.path.exists(gui_path):
            os.makedirs(gui_path)
            LOG.info(f"Created GUI directory: {gui_path}")
        
        # Set up static file serving
        self.static_app = DirectoryApp(gui_path)
        LOG.info(f"GUI controller initialized, serving from: {gui_path}")
    
    @route('middleware_gui', '/', methods=['GET'])
    def serve_index(self, req, **kwargs):
        """Serve the main index.html file"""
        req.path_info = 'index.html'
        return self.static_app(req)
    
    @route('middleware_gui', '/gui', methods=['GET'])
    def serve_gui_root(self, req, **kwargs):
        """Serve the GUI root (redirect to index.html)"""
        req.path_info = 'index.html'
        return self.static_app(req)
    
    @route('middleware_gui', '/gui/{filename:.*}', methods=['GET'])
    def serve_static_files(self, req, **kwargs):
        """Serve static files (HTML, CSS, JS, images, etc.)"""
        filename = kwargs.get('filename', 'index.html')

        # If no filename specified, serve index.html
        if not filename or filename == '':
            filename = 'index.html'

        req.path_info = filename
        return self.static_app(req)

    @route('middleware_gui', '/{filename:.*}', methods=['GET'])
    def serve_root_static_files(self, req, **kwargs):
        """Serve static files from root path"""
        filename = kwargs.get('filename', 'index.html')

        # If no filename specified, serve index.html
        if not filename or filename == '':
            filename = 'index.html'

        req.path_info = filename
        return self.static_app(req)
