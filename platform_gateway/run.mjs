import { configuration } from './config.mjs';
import { createProxy } from './proxy.mjs';

try {
  const config = configuration(process.argv[2]);
  const server = createProxy(config);
  server.on('error', error => {
    console.error(`${config.name} could not start: ${error.code || error.message}`);
    process.exitCode = 1;
  });
  server.listen(config.port, config.host, () => {
    console.log(`${config.name} listening at http://${config.host}:${config.port}`);
    console.log('Local development gateway. Upstream availability is not implied.');
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => {
    await server.shutdown();
  });
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
