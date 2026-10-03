import asyncio
import json
import websockets


async def test():

    uri = "ws://127.0.0.1:8000/ws-test"

    async with websockets.connect(uri) as ws:

        print("Connected to SmartSpeak")

        setup = {
            "type": "setup",
            "sessionId": "TEST_SESSION",
            "callSid": "TEST_CALL",
            "customParameters": {
                "name": "Chaithanya",
                "topic": "Job Interview",
                "duration": "10"
            }
        }

        await ws.send(json.dumps(setup))

        print("Setup sent")

        await asyncio.sleep(1)

        prompt = {
            "type": "prompt",
            "voicePrompt": "Hi, I recently completed my MCA and I am looking for a Data Analyst job.",
            "lang": "en-IN",
            "last": True
        }

        print("Sending prompt...")

        await ws.send(json.dumps(prompt))

        print("Prompt sent")
        print("Waiting for AI...\n")

        try:

            while True:

                response = await asyncio.wait_for(
                    ws.recv(),
                    timeout=30
                )

                print("AI RESPONSE:")
                print(response)
                print()

                data = json.loads(response)

                if data.get("last") is True:
                    break

        except asyncio.TimeoutError:

            print("Timed out waiting for AI response.")


asyncio.run(test())