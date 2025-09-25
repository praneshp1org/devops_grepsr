import unittest
from unittest.mock import AsyncMock, patch
import asyncio
from worker import WorkerService

class TestWorkerService(unittest.TestCase):
    def setUp(self):
        self.worker = WorkerService()
        
    @patch('asyncpg.connect')
    async def test_connect_db(self, mock_connect):
        mock_connect.return_value = AsyncMock()
        await self.worker.connect_db()
        self.assertTrue(mock_connect.called)

if __name__ == '__main__':
    unittest.main()