import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def start_mock_server():
    # Use absolute paths for Windows compatibility
    base_dir = os.path.dirname(os.path.abspath(__file__))
    storage_dir = os.path.join(base_dir, "fake_storage")
    
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)

    authorizer = DummyAuthorizer()
    # Credentials: test / test
    authorizer.add_user("test", "test", storage_dir, perm="elradfmw")
    
    handler = FTPHandler
    handler.authorizer = authorizer
    
    server = FTPServer(("127.0.0.1", 2125), handler)
    print(f"MOCK SERVER ACTIVE: 127.0.0.1:2125")
    print(f"Files will appear in: {storage_dir}")
    server.serve_forever()

if __name__ == "__main__":
    start_mock_server()