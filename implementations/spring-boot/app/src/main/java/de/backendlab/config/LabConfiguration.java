package de.backendlab.config;
import de.backendlab.cache.*;
import de.backendlab.labs.cache.*;
import de.backendlab.catalog.ProductStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
@Configuration
public class LabConfiguration {
    @Bean ProductCache productCache(@Value("${lab.cache.strategy}") String strategy, Environment env) {
        if (strategy.equals("unsafe") && !env.acceptsProfiles(Profiles.of("lab")))
            throw new IllegalStateException("unsafe cache requires the lab profile");
        return CacheFactory.create(strategy);
    }
    @Bean RefreshCoordinator refreshCoordinator(ProductStore store, ProductCache cache,
            @Value("${lab.cache.strategy}") String strategy, @Value("${lab.sync.strategy}") String sync,
            @Value("${lab.sync.batch-size}") int batchSize, Environment env) {
        if (sync.equals("watermark") && !env.acceptsProfiles(Profiles.of("lab")))
            throw new IllegalStateException("watermark sync requires the lab profile");
        return new RefreshCoordinator(store,cache,strategy,sync,batchSize);
    }
}
