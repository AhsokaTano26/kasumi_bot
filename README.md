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
```

The application converts them to the `QQ_BOTS` adapter setting before NoneBot
starts. WebSocket mode and the `c2c_group_at_messages` intent both default to
`true`. `QQ_BOTS` JSON remains supported when configuring multiple bots.

## Documentation

See [Docs](https://nonebot.dev/)
