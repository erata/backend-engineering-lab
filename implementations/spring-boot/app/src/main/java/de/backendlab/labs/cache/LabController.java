package de.backendlab.labs.cache;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
@Profile("lab")
@RestController
public class LabController {
    private final RefreshCoordinator coordinator;
    public LabController(RefreshCoordinator coordinator){this.coordinator=coordinator;}
    @PostMapping("/lab/cache/refresh") public ResponseEntity<RefreshCoordinator.RefreshResult> refresh(){
        var result=coordinator.refresh();return ResponseEntity.status(result.ran()?HttpStatus.OK:HttpStatus.CONFLICT).body(result);
    }
}
