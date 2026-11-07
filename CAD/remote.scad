$fn=360;

// 41mm, 11mm

//30mm 12mm 


h=35;

module A() 
{
   translate([0,0,9.8])
   translate([0,10-41/2,0]) 
   rotate([-10,0,0])
   hull() {
    translate([-15+6-0.25,0,0])cylinder(d=12,100); 
    translate([15-6+0.25,0,0])cylinder(d=12,100); 
   }   
}



difference() { 
    cylinder(d1=43+10,d2=43-6,11+h);
    translate([0,0,-1])cylinder(d=40.4,12);    
    A();

    hull() {
        translate([0,0,-7]) rotate([-90,0,0])cylinder(d=4.5,50);
        translate([0,0,6.5]) rotate([-90,0,0])cylinder(d=4.5,50);
    }
    
    translate([0,-10,11+8.5]) rotate([90,0,0])cylinder(d=6,50);
    
    rotate([-10,0,0]) translate([-25,-32.5,-5])cube([50,10,100]);
    
    cylinder(d=100,h=0.25);
}    





