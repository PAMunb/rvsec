// Copyright (c) 2002-2014 JavaMOP Team. All Rights Reserved.
import java.util.*;

public class SafeIterator_2 {
    public static void main(String[] args){
        Set<Integer> testSet = new HashSet<Integer>(); 
        for(int i = 0; i < 10; ++i){
            testSet.add(new Integer(i));
        }
        Iterator i = testSet.iterator();
        
        int output = 0; 
        for(int j = 0; j < 10 && i.hasNext(); ++j){
            output += (Integer)i.next();
        }
        System.out.println(output);
    }
}
