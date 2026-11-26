package de.backendlab.labs.cache;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
@Component
public class CacheLifecycle implements ApplicationRunner {
    private static final Logger LOG=LoggerFactory.getLogger(CacheLifecycle.class);
    private final RefreshCoordinator refresh;
    private final int seedCount;
    public CacheLifecycle(RefreshCoordinator refresh,@Value("${lab.seed-count}") int seedCount){this.refresh=refresh;this.seedCount=seedCount;}
    @Override public void run(ApplicationArguments args){refresh.initialize(seedCount);LOG.info("Cache initialized: {} products",refresh.status().products());}
    @Scheduled(fixedDelayString="${lab.refresh-interval}",initialDelayString="${lab.refresh-interval}")
    public void tick(){try{refresh.refresh();}catch(RuntimeException e){LOG.warn("Cache refresh failed; next tick will retry",e);}}
}
