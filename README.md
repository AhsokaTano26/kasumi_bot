# kasumi_bot

## How to start

1. generate project using `nb create` .
2. create your plugin using `nb plugin create` .
3. writing your plugins under `src/plugins` folder.
4. run your bot using `nb run --reload` .

## QQ configuration

For one QQ bot, configure these environment variables in the deployment platform:

```env
QQ_BOT_ID=your-app-id
QQ_BOT_TOKEN=your-token
QQ_BOT_SECRET=your-app-secret
QQ_USE_WEBSOCKET=false
```

The application converts them to the `QQ_BOTS` adapter setting before NoneBot
starts. `c2c_group_at_messages` defaults to `true`. `QQ_BOTS` JSON remains
supported when configuring multiple bots.

### Choosing how events are delivered

The QQ adapter can receive events over a WebSocket connection or by webhook.
Only the mode you actually use should be enabled, and the two need different
drivers:

| Mode | `QQ_USE_WEBSOCKET` | Driver must provide |
| --- | --- | --- |
| WebSocket (adapter default) | `true` | `~websockets` as well as `~fastapi+~httpx` |
| Webhook | `false` | `~fastapi+~httpx` is enough |

`QQ_USE_WEBSOCKET` sets the default `use_websocket` for every bot that does not
specify its own, so a webhook deployment can leave WebSocket mode off without
switching to JSON. A bot configured through `QQ_BOTS` keeps whatever it sets
itself. Values accepted are `true/false`, `1/0`, `yes/no`, `on/off`; anything
else fails at startup rather than being silently ignored.

Leaving this on by default while delivering events by webhook opens a redundant
WebSocket connection, which QQ eventually closes with `4009 Session timed out`
and then retries every few seconds — harmless to the bot's function, but noisy
in the logs.

## Commands and help

The custom QQ dispatcher follows NoneBot's `COMMAND_START` setting. To accept
both `help` and `/help` (and both forms of every other command), configure:

```env
COMMAND_START=["","/"]
```

In groups, **@ this bot** and send `help`, `/help`, or `帮助` to view the command
list; help without a real @ mention is ignored, including replies to the bot.
In private chats, send the help command directly. Click a blue command name to fill
the QQ input box, add any required arguments, then send it. `help 查卡` and
`/help /查卡` show detailed usage; configured command aliases also appear in help.
The clickable entries use QQ's
[parameter command format](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/server-inter/message/trans/text-chain.md).
If QQ rejects the Markdown message, the bot falls back to plain text help.

## Documentation

See [Docs](https://nonebot.dev/)
