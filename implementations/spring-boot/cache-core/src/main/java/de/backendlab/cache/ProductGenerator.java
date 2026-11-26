package de.backendlab.cache;
import java.util.*;
import java.util.stream.IntStream;
public final class ProductGenerator {
    private ProductGenerator() {}
    public static List<Product> generate(int count) {
        if (count < 0) throw new IllegalArgumentException("negative count");
        return IntStream.rangeClosed(1,count).mapToObj(i -> new Product(i,"Product "+i,null)).toList();
    }
}
