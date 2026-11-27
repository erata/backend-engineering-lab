package de.backendlab.labs;
import io.lettuce.core.ClientOptions;import org.springframework.beans.factory.annotation.Value;import org.springframework.boot.data.redis.autoconfigure.LettuceClientConfigurationBuilderCustomizer;import org.springframework.context.annotation.Bean;import org.springframework.context.annotation.Configuration;

/**
 * Lab 08: Lettuce's behaviour while the connection is down, selectable for the outage experiment.
 * <ul>
 *   <li>{@code default} (Lettuce default with auto-reconnect: {@code ACCEPT_COMMANDS}) – commands are queued until the
 *       connection is back or the 500 ms command timeout expires.</li>
 *   <li>{@code reject} – {@code REJECT_COMMANDS}: commands fail immediately while disconnected; auto-reconnect stays on.</li>
 * </ul>
 * Spring Boot's other client options (connect timeout, timeout options) are kept: they are mutated, not replaced.
 */
@Configuration(proxyBeanMethods=false)
public class RedisClientOptions {
 @Bean LettuceClientConfigurationBuilderCustomizer labDisconnectedBehavior(@Value("${LAB_REDIS_DISCONNECTED:default}") String mode){
  return builder->{
   if(!"reject".equals(mode))return;
   ClientOptions current=builder.build().getClientOptions().orElseGet(ClientOptions::create);
   builder.clientOptions(current.mutate().autoReconnect(true).disconnectedBehavior(ClientOptions.DisconnectedBehavior.REJECT_COMMANDS).build());
  };
 }
}
