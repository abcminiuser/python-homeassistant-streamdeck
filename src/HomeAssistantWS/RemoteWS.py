#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

import asyncio
import asyncws
import json
import itertools


class HomeAssistantWS(object):
    def __init__(self, host, port=8123, loop=asyncio.get_event_loop()):
        self._host = host
        self._port = port
        self._loop = loop

        self._id = itertools.count(start=1, step=1)
        self._websocket = None
        self._event_subscriptions = dict()
        self._message_responses = dict()
        self._entity_states = dict()

    async def _receive_message(self):
        message = await self._websocket.recv()
        return json.loads(message)

    async def _send_message(self, message):
        message_id = next(self._id)

        response_future = asyncio.Future(loop=self._loop)
        self._message_responses[message_id] = response_future

        message['id'] = message_id
        await self._websocket.send(json.dumps(message))

        return response_future

    async def _receiver(self):
        while True:
            message = await self._receive_message()
#            print(message, flush=True)

            if message['type'] == 'event':
                event_type = message['event']['event_type']
                event_data = message['event']['data']

                for future in self._event_subscriptions.get(event_type, []):
                    if future is not None:
                        asyncio.ensure_future(future(event_data))
            elif message['type'] == 'result':
                request_id = message['id']
                request_succcess = message['success']
                request_result = message['result']

                future = self._message_responses.get(request_id)
                if future is not None:
                    future.set_result((request_succcess, request_result))
                    del self._message_responses[request_id]

    async def _update_all_states(self):
        def _got_states(future):
            success, result = future.result()
            for state in result:
                entity_id = state['entity_id']
                entity_state = state['state']

                self._entity_states[entity_id] = entity_state

        message = {'type': 'get_states'}
        response = await self._send_message(message)
        response.add_done_callback(_got_states)

        return response

    async def _update_state(self, data):
        entity_id = data['entity_id']
        new_state = data['new_state'].get('state')
        self._entity_states[entity_id] = new_state

    async def connect(self, api_password=None):
        self._websocket = await asyncws.connect('ws://{}:{}/api/websocket'.format(self._host, self._port))
        self._loop.create_task(self._receiver())

        if api_password is not None:
            # First request should be the API password, if provided
            message = {'type': 'auth', 'api_password': api_password}
            response = await self._send_message(message)

        initial_requests = [
            # We want to track all state changes, to update our local cache
            await self.subscribe_to_event('state_changed', self._update_state),

            # We need to retrieve the intial entity states, so we can cache them
            await self._update_all_states()
        ]

        await asyncio.wait(initial_requests, timeout=5)

    async def subscribe_to_event(self, event_type, future):
        self._event_subscriptions[event_type] = self._event_subscriptions.get(
            event_type, []) + [future]

        message = {'type': 'subscribe_events', 'event_type': event_type}
        response = await self._send_message(message)
        return response

    async def set_state(self, domain, service, entity_id):
        message = {'type': 'call_service', 'domain': domain, 'service': service}
        if entity_id is not None:
            message['service_data'] = {'entity_id': entity_id}

        response = await self._send_message(message)
        return response

    async def get_state(self, entity_id):
        return self._entity_states.get(entity_id)

    async def get_all_states(self):
        return self._entity_states
