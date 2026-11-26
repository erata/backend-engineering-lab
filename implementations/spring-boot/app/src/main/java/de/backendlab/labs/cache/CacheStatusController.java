package de.backendlab.labs.cache;
import org.springframework.web.bind.annotation.*;
@RestController
public class CacheStatusController {
    private final RefreshCoordinator coordinator;
    public CacheStatusController(RefreshCoordinator coordinator){this.coordinator=coordinator;}
    @GetMapping("/api/cache/status") public RefreshCoordinator.Status status(){return coordinator.status();}
}
